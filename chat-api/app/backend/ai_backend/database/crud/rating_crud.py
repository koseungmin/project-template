# _*_ coding: utf-8 _*_
"""Message Rating CRUD operations with database."""
import logging
from datetime import datetime
from typing import Optional

from ai_backend.database.models.chat_models import ChatMessage, MessageRating
from ai_backend.types.response.exceptions import HandledException
from ai_backend.types.response.response_code import ResponseCode
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RatingCRUD:
    """메시지 평가 관련 CRUD 작업을 처리하는 클래스"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_rating(
        self,
        rating_id: str,
        message_id: str,
        user_id: str,
        rating_score: int,
        rating_comment: str = None
    ) -> MessageRating:
        """메시지 평가 생성"""
        try:
            # 메시지가 존재하고 AI 메시지인지 확인
            message = self.session.query(ChatMessage).filter(
                ChatMessage.message_id == message_id,
                ChatMessage.is_deleted == False
            ).first()
            
            if not message:
                raise HandledException(
                    ResponseCode.RESOURCE_NOT_FOUND,
                    message=f"메시지를 찾을 수 없습니다: {message_id}"
                )
            
            if message.message_type != "assistant":
                raise HandledException(
                    ResponseCode.INVALID_REQUEST,
                    message="AI 메시지만 평가할 수 있습니다."
                )
            
            # 평가 점수 검증 (1-5점)
            if rating_score < 1 or rating_score > 5:
                raise HandledException(
                    ResponseCode.INVALID_REQUEST,
                    message="평가 점수는 1-5점 사이여야 합니다."
                )
            
            rating = MessageRating(
                rating_id=rating_id,
                message_id=message_id,
                user_id=user_id,
                rating_score=rating_score,
                rating_comment=rating_comment,
                create_dt=datetime.now()
            )
            self.session.add(rating)
            self.session.commit()
            self.session.refresh(rating)
            return rating
        except HandledException:
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Database error creating rating: {str(e)}")
            self.session.rollback()
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_rating(self, message_id: str) -> Optional[MessageRating]:
        """특정 메시지의 평가 조회"""
        try:
            return self.session.query(MessageRating).filter(
                MessageRating.message_id == message_id,
                MessageRating.is_deleted == False
            ).first()
        except Exception as e:
            logger.error(f"Database error getting rating: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def update_rating(
        self,
        message_id: str,
        user_id: str,
        rating_score: int,
        rating_comment: str = None
    ) -> MessageRating:
        """메시지 평가 수정"""
        try:
            rating = self.get_rating(message_id)
            
            if not rating:
                raise HandledException(
                    ResponseCode.RESOURCE_NOT_FOUND,
                    message=f"평가를 찾을 수 없습니다: {message_id}"
                )
            
            # 평가한 사용자만 수정 가능
            if rating.user_id != user_id:
                raise HandledException(
                    ResponseCode.UNAUTHORIZED,
                    message="본인의 평가만 수정할 수 있습니다."
                )
            
            # 평가 점수 검증 (1-5점)
            if rating_score < 1 or rating_score > 5:
                raise HandledException(
                    ResponseCode.INVALID_REQUEST,
                    message="평가 점수는 1-5점 사이여야 합니다."
                )
            
            rating.rating_score = rating_score
            if rating_comment is not None:
                rating.rating_comment = rating_comment
            rating.updated_at = datetime.now()
            
            self.session.commit()
            self.session.refresh(rating)
            return rating
        except HandledException:
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Database error updating rating: {str(e)}")
            self.session.rollback()
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def delete_rating(self, message_id: str, user_id: str) -> bool:
        """메시지 평가 삭제 (소프트 삭제)"""
        try:
            rating = self.get_rating(message_id)
            
            if not rating:
                return False
            
            # 평가한 사용자만 삭제 가능
            if rating.user_id != user_id:
                raise HandledException(
                    ResponseCode.UNAUTHORIZED,
                    message="본인의 평가만 삭제할 수 있습니다."
                )
            
            rating.is_deleted = True
            self.session.commit()
            return True
        except HandledException:
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Database error deleting rating: {str(e)}")
            self.session.rollback()
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_chat_ratings(self, chat_id: str) -> dict:
        """특정 채팅의 모든 평가 조회 (메시지 ID별로 매핑)"""
        try:
            # 채팅에 속한 메시지들의 평가 조회
            ratings = self.session.query(MessageRating).join(
                ChatMessage,
                MessageRating.message_id == ChatMessage.message_id
            ).filter(
                ChatMessage.chat_id == chat_id,
                ChatMessage.is_deleted == False,
                MessageRating.is_deleted == False
            ).all()
            
            # 메시지 ID를 키로 하는 딕셔너리 반환
            rating_map = {}
            for rating in ratings:
                rating_map[rating.message_id] = {
                    "rating_id": rating.rating_id,
                    "rating_score": rating.rating_score,
                    "rating_comment": rating.rating_comment,
                    "created_at": rating.create_dt.isoformat() if rating.create_dt else None,
                    "updated_at": rating.updated_at.isoformat() if rating.updated_at else None
                }
            
            return rating_map
        except Exception as e:
            logger.error(f"Database error getting chat ratings: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)

