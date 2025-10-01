# -*- coding: utf-8 -*-
"""Database module."""

# from typing import Any, Callable, Dict, ContextManager
import os
import logging
# from pathlib import Path
from contextlib import contextmanager

# import pandas as pd

logger = logging.getLogger(__name__)

from sqlalchemy import create_engine, orm
from sqlalchemy.engine import engine_from_config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

# 모델 import는 __init__.py에서 처리


__all__ = [
    "Base",
    "Database",
]

Base = declarative_base()


class Database:
    def __init__(self, db_config):
        """
        """
        db_info = db_config['database']
        database_url = 'postgresql://{username}:{password}@{host}:{port}/{dbname}'.format(
            username=os.getenv("DATABASE__USERNAME", os.getenv("SYSTEMDB_USERNAME", db_info.get("username"))),
            password=os.getenv("DATABASE__PASSWORD", os.getenv("SYSTEMDB_PASSWORD", db_info.get("password"))),
            host=os.getenv("DATABASE__HOST", db_info.get("host")),
            port=os.getenv("DATABASE__PORT", db_info.get("port")),
            dbname=os.getenv("DATABASE__DBNAME", db_info.get("dbname")),
        )
        self._engine = create_engine(database_url)
        self._session_factory = orm.sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

    def create_database(self, checkfirst=True):
        """
        테이블 생성
        checkfirst: True면 기존 테이블이 있으면 건너뛰고, False면 무조건 생성 시도
        """
        try:
            # Backend 모델들 생성 (User, Chat, ChatMessage, Group)
            Base.metadata.create_all(bind=self._engine, checkfirst=checkfirst)
            
            # shared_core 모델들도 생성 (Document, DocumentChunk, ProcessingJob)
            from shared_core.models import Base as SharedBase
            SharedBase.metadata.create_all(bind=self._engine, checkfirst=checkfirst)
            
            logger.info("✅ 모든 테이블 생성 완료 (Backend + shared_core)")
        except Exception as e:
            logger.error("❌ 테이블 생성 실패: " + str(e))
            raise e

    @contextmanager
    def session(self):
        """
        """
        session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()    
    def close(self):
        """데이터베이스 연결 종료"""
        if hasattr(self, '_session_factory'):
            self._session_factory.close_all()
        if hasattr(self, '_engine'):
            self._engine.dispose()