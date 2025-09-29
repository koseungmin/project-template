# _*_ coding: utf-8 _*_
"""
공통 문서 모델 패키지
Backend와 Prefect 프로젝트에서 공통으로 사용하는 문서 관련 모델들
"""

__version__ = "1.0.0"
__author__ = "Document Processing Team"

from .crud import DocumentChunkCRUD, DocumentCRUD, ProcessingJobCRUD
from .database import (
    DatabaseManager,
    get_database_manager,
    get_db_session,
    initialize_database,
)
from .models import Document, DocumentChunk, ProcessingJob
from .services import DocumentChunkService, DocumentService, ProcessingJobService

__all__ = [
    "Document",
    "DocumentChunk", 
    "ProcessingJob",
    "DocumentCRUD",
    "DocumentChunkCRUD",
    "ProcessingJobCRUD",
    "DocumentService",
    "DocumentChunkService",
    "ProcessingJobService",
    "DatabaseManager",
    "get_db_session",
    "initialize_database",
    "get_database_manager"
]
