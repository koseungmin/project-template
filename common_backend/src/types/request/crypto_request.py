# _*_ coding: utf-8 _*_
"""암복호화 요청 모델."""
from pydantic import BaseModel, Field
from typing import Optional


class EncryptRequest(BaseModel):
    """암호화 요청 모델"""
    data: str = Field(..., description="암호화할 데이터")
    algorithm: Optional[str] = Field(default=None, description="암호화 알고리즘 (선택사항)")


class DecryptRequest(BaseModel):
    """복호화 요청 모델"""
    encrypted_data: str = Field(..., description="복호화할 암호화된 데이터")
    algorithm: Optional[str] = Field(default=None, description="암호화 알고리즘 (선택사항)")

