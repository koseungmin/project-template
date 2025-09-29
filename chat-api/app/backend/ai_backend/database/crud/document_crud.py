# _*_ coding: utf-8 _*_
"""Document CRUD operations with database."""
import logging

from ai_backend.types.response.exceptions import HandledException
from ai_backend.types.response.response_code import ResponseCode
from sqlalchemy.orm import Session

# 공통 모듈 사용
from shared_core import DocumentCRUD as BaseDocumentCRUD

logger = logging.getLogger(__name__)


class DocumentCRUD(BaseDocumentCRUD):
    """Document 관련 CRUD 작업을 처리하는 클래스 (FastAPI 전용 확장)"""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    # 모든 메서드는 부모 클래스에서 상속받되, 예외 처리만 FastAPI 전용으로 오버라이드
    
    def create_document(self, *args, **kwargs):
        """문서 생성 (FastAPI 예외 처리)"""
        try:
            return super().create_document(*args, **kwargs)
        except Exception as e:
            logger.error(f"문서 생성 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_document(self, document_id: str):
        """문서 조회 (FastAPI 예외 처리)"""
        try:
            return super().get_document(document_id)
        except Exception as e:
            logger.error(f"문서 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_user_documents(self, user_id: str):
        """사용자의 문서 목록 조회 (FastAPI 예외 처리)"""
        try:
            return super().get_user_documents(user_id)
        except Exception as e:
            logger.error(f"사용자 문서 목록 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def search_documents(self, user_id: str, search_term: str):
        """문서 검색 (FastAPI 예외 처리)"""
        try:
            return super().search_documents(user_id, search_term)
        except Exception as e:
            logger.error(f"문서 검색 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def update_document(self, document_id: str, **kwargs):
        """문서 정보 업데이트 (FastAPI 예외 처리)"""
        try:
            return super().update_document(document_id, **kwargs)
        except Exception as e:
            logger.error(f"문서 업데이트 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def update_document_status(self, document_id: str, status: str, error_message: str = None):
        """문서 상태 업데이트 (FastAPI 예외 처리)"""
        try:
            return super().update_document_status(document_id, status, error_message)
        except Exception as e:
            logger.error(f"문서 상태 업데이트 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def update_processing_info(self, document_id: str, **kwargs):
        """문서 처리 정보 업데이트 (FastAPI 예외 처리)"""
        try:
            return super().update_processing_info(document_id, **kwargs)
        except Exception as e:
            logger.error(f"문서 처리 정보 업데이트 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def find_document_by_hash(self, file_hash: str, status_filter: str = None):
        """파일 해시를 기반으로 기존 문서 검색 (FastAPI 예외 처리)"""
        try:
            return super().find_document_by_hash(file_hash, status_filter)
        except Exception as e:
            logger.error(f"해시 기반 문서 검색 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def find_completed_document_by_hash(self, file_hash: str):
        """완료된 상태의 기존 문서 검색 (FastAPI 예외 처리)"""
        try:
            return super().find_completed_document_by_hash(file_hash)
        except Exception as e:
            logger.error(f"완료된 문서 검색 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def check_document_permission(self, document_id: str, required_permission: str):
        """문서의 특정 권한 체크 (FastAPI 예외 처리)"""
        try:
            return super().check_document_permission(document_id, required_permission)
        except Exception as e:
            logger.error(f"문서 권한 체크 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def check_document_permissions(self, document_id: str, required_permissions, require_all: bool = False):
        """문서의 여러 권한 체크 (FastAPI 예외 처리)"""
        try:
            return super().check_document_permissions(document_id, required_permissions, require_all)
        except Exception as e:
            logger.error(f"문서 권한들 체크 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def update_document_permissions(self, document_id: str, permissions):
        """문서 권한 업데이트 (FastAPI 예외 처리)"""
        try:
            return super().update_document_permissions(document_id, permissions)
        except Exception as e:
            logger.error(f"문서 권한 업데이트 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def add_document_permission(self, document_id: str, permission: str):
        """문서에 권한 추가 (FastAPI 예외 처리)"""
        try:
            return super().add_document_permission(document_id, permission)
        except Exception as e:
            logger.error(f"문서 권한 추가 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def remove_document_permission(self, document_id: str, permission: str):
        """문서에서 권한 제거 (FastAPI 예외 처리)"""
        try:
            return super().remove_document_permission(document_id, permission)
        except Exception as e:
            logger.error(f"문서 권한 제거 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_documents_with_permission(self, user_id: str, required_permission: str):
        """특정 권한을 가진 사용자 문서 목록 조회 (FastAPI 예외 처리)"""
        try:
            return super().get_documents_with_permission(user_id, required_permission)
        except Exception as e:
            logger.error(f"권한별 문서 목록 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_documents_by_type(self, user_id: str, document_type: str):
        """특정 문서 타입의 사용자 문서 목록 조회 (FastAPI 예외 처리)"""
        try:
            return super().get_documents_by_type(user_id, document_type)
        except Exception as e:
            logger.error(f"타입별 문서 목록 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def update_document_type(self, document_id: str, document_type: str):
        """문서 타입 업데이트 (FastAPI 예외 처리)"""
        try:
            return super().update_document_type(document_id, document_type)
        except ValueError as e:
            logger.error(f"문서 타입 업데이트 실패: {str(e)}")
            raise HandledException(ResponseCode.DOCUMENT_INVALID_FILE_TYPE, msg=str(e))
        except Exception as e:
            logger.error(f"문서 타입 업데이트 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_document_type_stats(self, user_id: str):
        """사용자의 문서 타입별 통계 조회 (FastAPI 예외 처리)"""
        try:
            return super().get_document_type_stats(user_id)
        except Exception as e:
            logger.error(f"문서 타입별 통계 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def delete_document(self, document_id: str):
        """문서 삭제 (FastAPI 예외 처리)"""
        try:
            return super().delete_document(document_id)
        except Exception as e:
            logger.error(f"문서 삭제 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)