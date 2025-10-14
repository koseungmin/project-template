# _*_ coding: utf-8 _*_
"""Message rating response models."""
from typing import Dict, Optional

from pydantic import BaseModel, Field


class RatingResponse(BaseModel):
    """평가 응답 모델"""
    rating_id: str = Field(..., description="평가 ID")
    message_id: str = Field(..., description="메시지 ID")
    rating_score: int = Field(..., description="평가 점수 (1-5)")
    rating_comment: Optional[str] = Field(default=None, description="평가 코멘트")
    created_at: str = Field(..., description="생성 시간")
    updated_at: Optional[str] = Field(default=None, description="수정 시간")


class CreateRatingResponse(BaseModel):
    """평가 생성 응답 모델"""
    message: str = Field(default="평가가 저장되었습니다.", description="응답 메시지")
    rating: RatingResponse = Field(..., description="저장된 평가")


class UpdateRatingResponse(BaseModel):
    """평가 수정 응답 모델"""
    message: str = Field(default="평가가 수정되었습니다.", description="응답 메시지")
    rating: RatingResponse = Field(..., description="수정된 평가")


class DeleteRatingResponse(BaseModel):
    """평가 삭제 응답 모델"""
    message: str = Field(default="평가가 삭제되었습니다.", description="응답 메시지")
    deleted: bool = Field(default=True, description="삭제 여부")


class GetRatingResponse(BaseModel):
    """평가 조회 응답 모델"""
    rating: Optional[RatingResponse] = Field(default=None, description="평가 정보")


class GetChatRatingsResponse(BaseModel):
    """채팅 평가 목록 응답 모델"""
    ratings: Dict[str, dict] = Field(..., description="메시지 ID별 평가 맵")

