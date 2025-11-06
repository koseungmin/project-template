# _*_ coding: utf-8 _*_
"""JWT Authentication middleware."""
import logging
from typing import Optional

import jwt
from fastapi import HTTPException, Request, status
from src.config import settings
from src.core.global_exception_handlers import create_error_response
from src.utils.jwt_key_manager import JWTKeyManager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT 토큰 검증 미들웨어"""
    
    def __init__(self, app):
        super().__init__(app)
        self.exclude_paths = settings.get_jwt_exclude_paths()
        # 퍼블릭 키 기반 알고리즘 사용 시 키 관리자 초기화
        if not settings.jwt_jwks_uri:
            raise ValueError("JWT_JWKS_URI가 설정되지 않았습니다. RS256/ES256 알고리즘 사용 시 필수입니다.")
        self.key_manager = JWTKeyManager(jwks_uri=settings.jwt_jwks_uri)
        logger.info(f"JWT Key Manager initialized with JWKS URI: {settings.jwt_jwks_uri}")
    
    def _is_excluded_path(self, path: str) -> bool:
        """경로가 제외 목록에 있는지 확인"""
        # 정확한 경로 매칭
        if path in self.exclude_paths:
            return True
        
        # 경로가 제외 경로로 시작하는지 확인 (예: /docs/..., /openapi.json)
        for excluded_path in self.exclude_paths:
            if path.startswith(excluded_path):
                return True
        
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Authorization 헤더에서 토큰 추출"""
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        # "Bearer <token>" 형식에서 토큰 추출
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]
    
    def _extract_kid(self, token: str) -> Optional[str]:
        """JWT 헤더에서 kid (Key ID) 추출"""
        try:
            # 검증 없이 헤더만 디코딩
            unverified_header = jwt.get_unverified_header(token)
            return unverified_header.get("kid")
        except Exception as e:
            logger.warning(f"Failed to extract kid from token: {e}")
            return None
    
    async def _verify_token(self, token: str) -> dict:
        """
        JWT 토큰 검증 (퍼블릭 키 기반)
        
        1. 토큰 헤더에서 kid 추출
        2. get_public_key(kid)로 퍼블릭 키 조회
        3. 조회한 키로 토큰 검증
        """
        try:
            if not self.key_manager:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="JWT Key Manager가 초기화되지 않았습니다."
                )
            
            # 토큰 헤더에서 kid 추출
            kid = self._extract_kid(token)
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="토큰에 kid (Key ID)가 없습니다."
                )
            
            # kid로 퍼블릭 키 조회 (캐시 확인 → 갱신 → 재확인)
            public_key = await self.key_manager.get_public_key(kid)
            
            # 퍼블릭 키로 토큰 검증
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            return payload
            
        except HTTPException:
            # HTTPException은 그대로 전파
            raise
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 만료되었습니다."
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다."
            )
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="토큰 검증 중 오류가 발생했습니다."
            )
    
    async def dispatch(self, request: Request, call_next):
        # JWT 검증이 비활성화된 경우 통과
        if not settings.jwt_enabled:
            return await call_next(request)
        
        # 제외 경로인 경우 통과
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # 토큰 추출
        token = self._extract_token(request)
        if not token:
            error_response = create_error_response(
                code=401,
                message="인증 토큰이 필요합니다.",
                content="Authorization 헤더에 Bearer 토큰을 포함해주세요.",
                http_status_code=401
            )
            return JSONResponse(
                status_code=401,
                content=error_response.dict()
            )
        
        # 토큰 검증
        try:
            payload = await self._verify_token(token)
            # 검증 성공 시 payload를 request state에 저장
            request.state.jwt_payload = payload
            request.state.user_id = payload.get("user_id") or payload.get("sub") or payload.get("id")
        except HTTPException as e:
            error_response = create_error_response(
                code=e.status_code,
                message=e.detail,
                content=f"토큰 검증에 실패했습니다: {e.detail}",
                http_status_code=e.status_code
            )
            return JSONResponse(
                status_code=e.status_code,
                content=error_response.dict()
            )
        
        # 요청 계속 처리
        response = await call_next(request)
        return response

