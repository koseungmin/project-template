# _*_ coding: utf-8 _*_
"""
공통 데이터베이스 연결 관리
Backend와 Prefect 프로젝트에서 공통으로 사용하는 데이터베이스 연결 관리
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """데이터베이스 연결 관리자"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self, database_url: str = None, **engine_kwargs):
        """데이터베이스 연결 초기화"""
        if self._initialized:
            logger.info("데이터베이스가 이미 초기화되었습니다.")
            return
        
        # 데이터베이스 URL 설정
        if not database_url:
            database_url = self._get_database_url_from_env()
        
        if not database_url:
            raise ValueError("데이터베이스 URL이 설정되지 않았습니다.")
        
        # 기본 엔진 설정
        default_engine_kwargs = {
            'poolclass': QueuePool,
            'pool_size': 10,
            'max_overflow': 20,
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'echo': False
        }
        default_engine_kwargs.update(engine_kwargs)
        
        try:
            self.engine = create_engine(database_url, **default_engine_kwargs)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self._initialized = True
            logger.info("✅ 데이터베이스 연결이 초기화되었습니다.")
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 실패: {str(e)}")
            raise
    
    def _get_database_url_from_env(self) -> Optional[str]:
        """환경변수에서 데이터베이스 URL 구성"""
        # PostgreSQL 환경변수들
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'document_db')
        username = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', '')
        
        # 직접 URL이 제공된 경우
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return database_url
        
        # 개별 환경변수로 URL 구성
        if password:
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql://{username}@{host}:{port}/{database}"
    
    def create_tables(self):
        """테이블 생성"""
        if not self._initialized:
            raise RuntimeError("데이터베이스가 초기화되지 않았습니다.")
        
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ 데이터베이스 테이블이 생성되었습니다.")
        except Exception as e:
            logger.error(f"❌ 테이블 생성 실패: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        if not self._initialized:
            return False
        
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"❌ 데이터베이스 연결 테스트 실패: {str(e)}")
            return False
    
    def get_session(self) -> Session:
        """새 데이터베이스 세션 생성"""
        if not self._initialized:
            raise RuntimeError("데이터베이스가 초기화되지 않았습니다.")
        
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """세션 컨텍스트 매니저"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.engine:
            self.engine.dispose()
            self._initialized = False
            logger.info("데이터베이스 연결이 종료되었습니다.")


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()


def get_db_session() -> Generator[Session, None, None]:
    """의존성 주입용 세션 생성기"""
    with db_manager.session_scope() as session:
        yield session


def initialize_database(database_url: str = None, **engine_kwargs):
    """데이터베이스 초기화 헬퍼 함수"""
    db_manager.initialize(database_url, **engine_kwargs)
    db_manager.create_tables()


def get_database_manager() -> DatabaseManager:
    """데이터베이스 매니저 인스턴스 반환"""
    return db_manager
