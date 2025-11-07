# _*_ coding: utf-8 _*_
"""Authentication response models."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """인증된 사용자 정보."""

    user_id: str
    employee_id: str
    name: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None


class AuthTokenResponse(BaseModel):
    """로그인 성공 시 반환되는 토큰 응답."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: datetime
    issued_at: datetime
    user: AuthenticatedUser

