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

    def login(self, login_info: LoginInfo) -> Dict:
        """로그인 요청을 처리하고 토큰을 발급합니다."""
        try:
            user_id = login_info.user_id
            employee_id = login_info.employee_id
            name = login_info.name or login_info.user_id

            if not user_id or not employee_id:
                raise HandledException(ResponseCode.REQUIRED_FIELD_MISSING, msg="user_id 또는 employee_id가 누락되었습니다.")

            # 사용자 조회 (우선 user_id, 이후 employee_id로 fallback)
            user = self.user_crud.get_user(user_id)
            if not user and employee_id:
                user = self.user_crud.get_user_by_employee_id(employee_id)
                if user:
                    user_id = user.user_id

            # 사용자 없으면 생성
            if not user:
                user = self.user_crud.create_user(
                    user_id=user_id,
                    employee_id=employee_id,
                    name=name,
                )
                logger.info(f"신규 사용자 생성: user_id={user_id}, employee_id={employee_id}")
            else:
                # 사용자 정보 업데이트 (이름 변경 등)
                updated = False
                if login_info.name and login_info.name != user.name:
                    user = self.user_crud.update_user(user.user_id, name=login_info.name)
                    updated = True
                if employee_id and employee_id != user.employee_id:
                    user = self.user_crud.update_user(user.user_id, employee_id=employee_id)
                    updated = True
                if updated:
                    logger.info(f"사용자 정보 업데이트: user_id={user.user_id}")

            user_profile = self._build_user_profile(
                user.user_id,
                user.employee_id,
                login_info.name or user.name,
                login_info.department,
                login_info.email,
            )

            return self._issue_token(user.user_id, user.employee_id, user_profile)

        except HandledException:
            raise
        except Exception as exc:
            logger.exception("로그인 처리 중 오류가 발생했습니다.")
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

