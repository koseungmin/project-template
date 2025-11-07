# _*_ coding: utf-8 _*_
"""Dependency injection for FastAPI."""
import logging
from typing import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session
from src.api.services.auth_service import AuthService
from src.api.services.document_service import DocumentService
from src.api.services.group_service import GroupService
from src.api.services.llm_chat_service import LLMChatService
from src.api.services.user_service import UserService
from src.cache.redis_client import get_redis_client
from src.config import settings
from src.database.base import Database

logger = logging.getLogger(__name__)

# 전역 인스턴스들 (싱글톤)
_db_instance = None
_redis_instance = None


def get_database() -> Database:
    """데이터베이스 의존성 주입 (싱글톤 패턴)"""
    global _db_instance
    
    if _db_instance is not None:
        logger.debug("Returning existing database instance")
        return _db_instance
    
    logger.info("Creating new database instance")
    
    # 설정 유효성 검사 (Pydantic Settings는 자동으로 검증됨)
    
    # DB 설정
    try:
        db_config = settings.get_database_config()
        _db_instance = Database(db_config)
        _db_instance.create_database()
        print(f"[DEBUG] Database connection established: {settings.database_host}:{settings.database_port}")
        return _db_instance
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        raise ValueError(f"Database connection is required but failed: {e}")


def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성 주입 (요청별 세션)"""
    db = get_database()
    session = db._session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_redis_client():
    """Redis 클라이언트 의존성 주입 (싱글톤 패턴)"""
    global _redis_instance
    
    # 캐시가 비활성화된 경우 None 반환
    if not settings.is_cache_enabled():
        print("[DEBUG] Cache is disabled, returning None for Redis client")
        return None
    
    if _redis_instance is not None:
        return _redis_instance
    
    try:
        from src.cache.redis_client import RedisClient
        _redis_instance = RedisClient()
        if _redis_instance.ping():
            print("[DEBUG] Redis connection established")
            return _redis_instance
        else:
            print("[WARNING] Redis connection failed, returning None")
            _redis_instance = None
            return None
    except Exception as e:
        print(f"[WARNING] Redis connection failed: {e}, returning None")
        _redis_instance = None
        return None


def get_llm_chat_service(
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
) -> LLMChatService:
    """LLM 채팅 서비스 의존성 주입 (Redis fallback 지원)"""
    # LLMChatService는 환경 변수에서 LLM 제공자를 자동으로 선택
    return LLMChatService(
        db=db,
        redis_client=redis_client
    )


def get_document_service(
    db: Session = Depends(get_db)
) -> DocumentService:
    """문서 관리 서비스 의존성 주입"""
    return DocumentService(db=db)


def get_auth_service(
    db: Session = Depends(get_db)
) -> AuthService:
    """인증 서비스 의존성 주입"""
    return AuthService(db=db)


def get_user_service(
    db: Session = Depends(get_db)
) -> UserService:
    """사용자 관리 서비스 의존성 주입"""
    return UserService(db=db)


def get_group_service(
    db: Session = Depends(get_db)
) -> GroupService:
    """그룹 관리 서비스 의존성 주입"""
    return GroupService(db=db)


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
