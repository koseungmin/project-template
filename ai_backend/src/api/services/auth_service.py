# _*_ coding: utf-8 _*_
"""Authentication service for issuing self-signed tokens."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
from sqlalchemy.orm import Session
from src.config import settings
from src.database.crud.user_crud import UserCRUD
from src.types.request.auth_request import LoginInfo
from src.types.response.exceptions import HandledException
from src.types.response.response_code import ResponseCode

logger = logging.getLogger(__name__)


class AuthService:
    """인증 관련 비즈니스 로직을 처리하는 서비스."""

    def __init__(self, db: Session):
        if db is None:
            raise ValueError("Database session is required")

        self.db = db
        self.user_crud = UserCRUD(db)
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expires_minutes = settings.jwt_access_token_expires_minutes
        self.issuer = settings.jwt_issuer

        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY 설정이 필요합니다.")

    def _extract_sso_payload(self, sso_token: str) -> Dict:
        """
        SSO 토큰에서 payload를 추출합니다 (서명 검증 없이).
        
        Args:
            sso_token: SSO 인증 서비스에서 받은 토큰
            
        Returns:
            토큰의 payload 딕셔너리
            
        Raises:
            HandledException: 토큰 파싱 실패 시
        """
        try:
            # 서명 검증 없이 payload만 추출
            payload = jwt.decode(
                sso_token,
                options={"verify_signature": False}  # 서명 검증 스킵
            )
            logger.debug(f"SSO 토큰 payload 추출 성공: {payload}")
            return payload
        except jwt.DecodeError as exc:
            logger.warning(f"SSO 토큰 디코딩 실패: {str(exc)}")
            raise HandledException(
                ResponseCode.AUTH_TOKEN_INVALID,
                msg="SSO 토큰 형식이 올바르지 않습니다.",
                e=exc
            )
        except Exception as exc:
            logger.error(f"SSO 토큰 payload 추출 중 오류: {str(exc)}")
            raise HandledException(
                ResponseCode.AUTH_TOKEN_INVALID,
                msg="SSO 토큰 처리 중 오류가 발생했습니다.",
                e=exc
            )

    def login(self, sso_token: str, login_info: Optional[LoginInfo] = None) -> Dict:
        """
        SSO 토큰 기반 로그인 요청을 처리하고 자체 토큰을 발급합니다.
        
        Args:
            sso_token: SSO 인증 서비스에서 받은 토큰
            login_info: 기존 로그인 정보 (하위 호환성, 사용 안 함)
            
        Returns:
            자체 발급 토큰 및 사용자 정보
        """
        try:
            # SSO 토큰에서 payload 추출 (서명 검증 없이)
            sso_payload = self._extract_sso_payload(sso_token)
            
            # payload에서 user 정보 추출
            # 일반적인 JWT 클레임 필드명들을 시도
            user_id = (
                sso_payload.get("user_id") or 
                sso_payload.get("userId") or 
                sso_payload.get("sub") or 
                sso_payload.get("id") or
                sso_payload.get("username")
            )
            
            employee_id = (
                sso_payload.get("employee_id") or 
                sso_payload.get("employeeId") or 
                sso_payload.get("empId") or 
                sso_payload.get("sabun")
            )
            
            name = (
                sso_payload.get("name") or 
                sso_payload.get("userName") or 
                sso_payload.get("displayName") or
                user_id  # 기본값으로 user_id 사용
            )
            
            department = (
                sso_payload.get("department") or 
                sso_payload.get("dept") or 
                sso_payload.get("departmentName") or
                sso_payload.get("team")
            )
            
            email = (
                sso_payload.get("email") or 
                sso_payload.get("mail") or 
                sso_payload.get("emailAddress")
            )
            
            if not user_id:
                raise HandledException(
                    ResponseCode.REQUIRED_FIELD_MISSING,
                    msg="SSO 토큰에서 user_id를 찾을 수 없습니다."
                )
            
            if not employee_id:
                raise HandledException(
                    ResponseCode.REQUIRED_FIELD_MISSING,
                    msg="SSO 토큰에서 employee_id를 찾을 수 없습니다."
                )
            
            logger.info(f"SSO 토큰에서 추출한 사용자 정보: user_id={user_id}, employee_id={employee_id}")
            
            # DB에서 사용자 조회
            user = self.user_crud.get_user(user_id)
            if not user:
                raise HandledException(
                    ResponseCode.USER_NOT_FOUND,
                    msg=f"사용자 ID {user_id}가 데이터베이스에 존재하지 않습니다."
                )
            
            # employee_id 일치 확인
            if employee_id != user.employee_id:
                logger.warning(
                    f"SSO 토큰의 employee_id({employee_id})와 DB의 employee_id({user.employee_id})가 일치하지 않습니다."
                )
                raise HandledException(
                    ResponseCode.USER_INVALID_CREDENTIALS,
                    msg="사번이 일치하지 않습니다.",
                )
            
            # 사용자 프로필 구성 (SSO 토큰의 정보 우선, 없으면 DB 정보 사용)
            user_profile = self._build_user_profile(
                user.user_id,
                user.employee_id,
                name or user.name,  # SSO에서 온 name 우선
                department,  # SSO에서 온 department
                email,  # SSO에서 온 email
            )
            
            # 우리 자체 토큰 발급
            return self._issue_token(user.user_id, user.employee_id, user_profile)

        except HandledException:
            raise
        except Exception as exc:
            logger.exception("SSO 토큰 기반 로그인 처리 중 오류가 발생했습니다.")
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=exc)

    def refresh_access_token(self, access_token: str) -> Dict:
        """기존 액세스 토큰을 검증하고 새 토큰을 발급합니다."""
        try:
            decode_kwargs = {
                "algorithms": [self.algorithm],
                "options": {
                    "require": ["exp", "iat"],
                },
            }
            if self.issuer:
                decode_kwargs["issuer"] = self.issuer

            payload = jwt.decode(
                access_token,
                self.secret_key,
                **decode_kwargs,
            )

            user_id = payload.get("sub") or payload.get("user_id")
            if not user_id:
                raise HandledException(ResponseCode.AUTH_TOKEN_INVALID, msg="user_id 누락")

            user = self.user_crud.get_user(user_id)
            if not user:
                raise HandledException(ResponseCode.USER_NOT_FOUND)

            user_profile = self._build_user_profile(
                user.user_id,
                user.employee_id,
                payload.get("name") or user.name,
                payload.get("department"),
                payload.get("email"),
            )

            return self._issue_token(user.user_id, user.employee_id, user_profile)

        except jwt.ExpiredSignatureError as exc:
            raise HandledException(ResponseCode.AUTH_TOKEN_EXPIRED, e=exc)
        except jwt.InvalidTokenError as exc:
            raise HandledException(ResponseCode.AUTH_TOKEN_INVALID, e=exc)
        except HandledException:
            raise
        except Exception as exc:
            logger.exception("토큰 재발급 중 오류가 발생했습니다.")
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=exc)

    def _build_user_profile(
        self,
        user_id: str,
        employee_id: str,
        name: str,
        department: Optional[str],
        email: Optional[str],
    ) -> Dict:
        return {
            "user_id": user_id,
            "employee_id": employee_id,
            "name": name,
            "department": department,
            "email": email,
        }

    def _issue_token(
        self,
        user_id: str,
        employee_id: str,
        user_profile: Dict,
    ) -> Dict:
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(minutes=self.expires_minutes)

        payload = {
            "token_type": "access",
            "sub": user_id,
            "user_id": user_id,
            "employee_id": employee_id,
            "name": user_profile.get("name"),
            "department": user_profile.get("department"),
            "email": user_profile.get("email"),
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        if self.issuer:
            payload["iss"] = self.issuer

        access_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return {
            "access_token": access_token,
            "expires_in": int((expires_at - issued_at).total_seconds()),
            "expires_at": expires_at,
            "issued_at": issued_at,
            "user": user_profile,
        }

