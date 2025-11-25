# _*_ coding: utf-8 _*_
"""Common response models."""
from pydantic import BaseModel, Field
from typing import Optional


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    code: int = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    content: str = Field(..., description="사용자에게 표시할 에러 내용")
    timestamp: str = Field(..., description="타임스탬프")
    trace_id: Optional[str] = Field(default=None, description="추적 ID")

