# _*_ coding: utf-8 _*_
"""Authentication API endpoints."""
import logging

from fastapi import APIRouter, Depends
from src.api.services.auth_service import AuthService
from src.core.dependencies import get_auth_service
from src.types.request.auth_request import LoginRequest, TokenRefreshRequest
from src.types.response.auth_response import AuthTokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=AuthTokenResponse)
def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    """로그인 요청을 처리하고 자체 토큰을 발급합니다."""
    logger.info("로그인 요청 수신")
    result = auth_service.login(request.login_info)
    return AuthTokenResponse(**result)


@router.post("/auth/refresh", response_model=AuthTokenResponse)
def refresh_token(
    request: TokenRefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    """현재 액세스 토큰을 검증하여 새 토큰을 발급합니다."""
    logger.info("액세스 토큰 재발급 요청 수신")
    result = auth_service.refresh_access_token(request.access_token)
    return AuthTokenResponse(**result)

