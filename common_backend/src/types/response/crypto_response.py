# _*_ coding: utf-8 _*_
"""암복호화 응답 모델."""
from pydantic import BaseModel, Field


class EncryptResponse(BaseModel):
    """암호화 응답 모델"""
    encrypted_data: str = Field(..., description="암호화된 데이터")
    algorithm: str = Field(..., description="사용된 암호화 알고리즘")


class DecryptResponse(BaseModel):
    """복호화 응답 모델"""
    decrypted_data: str = Field(..., description="복호화된 데이터")
    algorithm: str = Field(..., description="사용된 암호화 알고리즘")

