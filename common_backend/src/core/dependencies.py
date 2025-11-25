# _*_ coding: utf-8 _*_
"""Dependency injection for FastAPI."""
import logging
from typing import Optional

from fastapi import Depends, Request
from src.config import settings

logger = logging.getLogger(__name__)


def get_current_user(request: Request) -> dict:
    """
    JWT 토큰에서 사용자 정보를 추출하는 의존성 함수
    
    사용법:
        @router.get("/example")
        def example_endpoint(user: dict = Depends(get_current_user)):
            user_id = user.get("user_id")
            ...
    
    Returns:
        dict: JWT payload (user_id, sub, id 등 포함)
    
    Raises:
        HTTPException: 토큰이 없거나 유효하지 않은 경우
    """
    # 미들웨어에서 검증된 payload 가져오기
    if not hasattr(request.state, "jwt_payload"):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다."
        )
    
    return request.state.jwt_payload


def get_current_user_id(request: Request) -> str:
    """
    JWT 토큰에서 사용자 ID를 추출하는 의존성 함수
    
    사용법:
        @router.get("/example")
        def example_endpoint(user_id: str = Depends(get_current_user_id)):
            ...
    
    Returns:
        str: 사용자 ID
    
    Raises:
        HTTPException: 토큰이 없거나 유효하지 않은 경우
    """
    payload = get_current_user(request)
    # 다양한 필드명 지원 (user_id, sub, id)
    user_id = payload.get("user_id") or payload.get("sub") or payload.get("id")
    
    if not user_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자 ID를 찾을 수 없습니다."
        )
    
    return user_id

