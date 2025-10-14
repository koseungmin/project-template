# _*_ coding: utf-8 _*_
"""Message Rating REST API endpoints."""
import logging

from ai_backend.core.dependencies import get_db
from ai_backend.database.crud.rating_crud import RatingCRUD
from ai_backend.types.request.rating_request import (
    CreateRatingRequest,
    UpdateRatingRequest,
)
from ai_backend.types.response.rating_response import (
    CreateRatingResponse,
    DeleteRatingResponse,
    GetChatRatingsResponse,
    GetRatingResponse,
    RatingResponse,
    UpdateRatingResponse,
)
from ai_backend.utils.uuid_gen import gen
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["message-rating"])


@router.post("/ratings", response_model=CreateRatingResponse)
def create_rating(
    request: CreateRatingRequest,
    db: Session = Depends(get_db)
):
    """메시지 평가 생성 또는 수정"""
    rating_crud = RatingCRUD(db)
    
    # 기존 평가가 있는지 확인
    existing_rating = rating_crud.get_rating(request.message_id)
    
    if existing_rating:
        # 기존 평가가 있으면 수정
        rating = rating_crud.update_rating(
            message_id=request.message_id,
            user_id=request.user_id,
            rating_score=request.rating_score,
            rating_comment=request.rating_comment
        )
        message = "평가가 수정되었습니다."
    else:
        # 새 평가 생성
        rating_id = gen()
        rating = rating_crud.create_rating(
            rating_id=rating_id,
            message_id=request.message_id,
            user_id=request.user_id,
            rating_score=request.rating_score,
            rating_comment=request.rating_comment
        )
        message = "평가가 저장되었습니다."
    
    return CreateRatingResponse(
        message=message,
        rating=RatingResponse(
            rating_id=rating.rating_id,
            message_id=rating.message_id,
            rating_score=rating.rating_score,
            rating_comment=rating.rating_comment,
            created_at=rating.create_dt.isoformat() if rating.create_dt else None,
            updated_at=rating.updated_at.isoformat() if rating.updated_at else None
        )
    )


@router.get("/ratings/{message_id}", response_model=GetRatingResponse)
def get_rating(
    message_id: str,
    db: Session = Depends(get_db)
):
    """메시지 평가 조회"""
    rating_crud = RatingCRUD(db)
    rating = rating_crud.get_rating(message_id)
    
    if not rating:
        return GetRatingResponse(rating=None)
    
    return GetRatingResponse(
        rating=RatingResponse(
            rating_id=rating.rating_id,
            message_id=rating.message_id,
            rating_score=rating.rating_score,
            rating_comment=rating.rating_comment,
            created_at=rating.create_dt.isoformat() if rating.create_dt else None,
            updated_at=rating.updated_at.isoformat() if rating.updated_at else None
        )
    )


@router.put("/ratings/{message_id}", response_model=UpdateRatingResponse)
def update_rating(
    message_id: str,
    request: UpdateRatingRequest,
    db: Session = Depends(get_db)
):
    """메시지 평가 수정"""
    rating_crud = RatingCRUD(db)
    rating = rating_crud.update_rating(
        message_id=message_id,
        user_id=request.user_id,
        rating_score=request.rating_score,
        rating_comment=request.rating_comment
    )
    
    return UpdateRatingResponse(
        rating=RatingResponse(
            rating_id=rating.rating_id,
            message_id=rating.message_id,
            rating_score=rating.rating_score,
            rating_comment=rating.rating_comment,
            created_at=rating.create_dt.isoformat() if rating.create_dt else None,
            updated_at=rating.updated_at.isoformat() if rating.updated_at else None
        )
    )


@router.delete("/ratings/{message_id}", response_model=DeleteRatingResponse)
def delete_rating(
    message_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """메시지 평가 삭제"""
    rating_crud = RatingCRUD(db)
    success = rating_crud.delete_rating(message_id, user_id)
    
    if success:
        return DeleteRatingResponse(
            message="평가가 삭제되었습니다.",
            deleted=True
        )
    else:
        return DeleteRatingResponse(
            message="평가를 찾을 수 없습니다.",
            deleted=False
        )


@router.get("/chats/{chat_id}/ratings", response_model=GetChatRatingsResponse)
def get_chat_ratings(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """채팅의 모든 평가 조회"""
    rating_crud = RatingCRUD(db)
    ratings = rating_crud.get_chat_ratings(chat_id)
    
    return GetChatRatingsResponse(ratings=ratings)

