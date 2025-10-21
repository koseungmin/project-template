#!/usr/bin/env python3
"""
PostgreSQL 데이터베이스 모델 및 연결 관리 - 공통 모듈 사용
"""

import logging
from typing import Any, Dict, Optional

from config import config

# 공통 모듈 사용
from shared_core import (
    DatabaseManager,
    Document,
    DocumentChunk,
    ProcessingJob,
    get_db_session,
    initialize_database,
)

logger = logging.getLogger(__name__)

# 기존 코드와의 호환성을 위한 별칭들
DocumentMetadata = Document

# Prefect 전용 데이터베이스 매니저 설정
class PrefectDatabaseManager:
    """Prefect 전용 데이터베이스 매니저"""
    
    def __init__(self):
        self._db_manager = None
    
    def initialize(self):
        """Prefect 설정을 사용하여 데이터베이스 초기화"""
        try:
            # Prefect 설정에서 데이터베이스 URL 구성
            database_url = self._get_database_url_from_config()
            
            # 공통 모듈의 initialize_database 사용
            initialize_database(database_url)
            
            logger.info("✅ Prefect 데이터베이스 연결이 초기화되었습니다.")
            return True
        except Exception as e:
            logger.error(f"❌ Prefect 데이터베이스 초기화 실패: {str(e)}")
            return False
    
    def _get_database_url_from_config(self) -> str:
        """Prefect 설정에서 데이터베이스 URL 구성"""
        # config.py에서 PostgreSQL 설정 가져오기
        postgres_config = config.postgres
        
        return (
            f"postgresql://{postgres_config['user']}:{postgres_config['password']}"
            f"@{postgres_config['host']}:{postgres_config['port']}/{postgres_config['database']}"
        )
    
    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        from shared_core import get_database_manager
        return get_database_manager().test_connection()

# Prefect 전용 데이터베이스 매니저 인스턴스
db_manager = PrefectDatabaseManager()

# 기존 코드와의 호환성을 위한 함수들
def get_db_session():
    """데이터베이스 세션 생성 (공통 모듈 사용)"""
    from shared_core import get_db_session as base_get_db_session
    return base_get_db_session()

# 모든 모델과 함수들을 export
__all__ = [
    "Document",
    "DocumentChunk", 
    "ProcessingJob",
    "DocumentMetadata",  # 호환성을 위한 별칭
    "db_manager",
    "get_db_session"
]