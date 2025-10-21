# _*_ coding: utf-8 _*_
"""Message rating request models."""
from typing import Optional

from pydantic import BaseModel, Field


class CreateRatingRequest(BaseModel):
    """평가 생성 요청 모델"""
    message_id: str = Field(..., min_length=1, max_length=50, description="메시지 ID")
    user_id: str = Field(..., min_length=1, max_length=50, description="사용자 ID")
    rating_score: int = Field(..., ge=1, le=5, description="평가 점수 (1-5)")
    rating_comment: Optional[str] = Field(default=None, max_length=500, description="평가 코멘트 (선택)")


class UpdateRatingRequest(BaseModel):
    """평가 수정 요청 모델"""
    user_id: str = Field(..., min_length=1, max_length=50, description="사용자 ID")
    rating_score: int = Field(..., ge=1, le=5, description="평가 점수 (1-5)")
    rating_comment: Optional[str] = Field(default=None, max_length=500, description="평가 코멘트 (선택)")

