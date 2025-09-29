# _*_ coding: utf-8 _*_
"""
공통 CRUD 작업
Backend와 Prefect 프로젝트에서 공통으로 사용하는 데이터베이스 CRUD 작업들
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from .models import Document, DocumentChunk, ProcessingJob

logger = logging.getLogger(__name__)


class DocumentCRUD:
    """Document 관련 CRUD 작업을 처리하는 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_document(
        self,
        document_id: str,
        document_name: str,
        original_filename: str,
        file_key: str,
        file_size: int,
        file_type: str,
        file_extension: str,
        user_id: str,
        upload_path: str,
        is_public: bool = False,
        status: str = 'processing',
        error_message: str = None,
        # 새로운 optional 필드들
        file_hash: str = None,
        total_pages: int = None,
        processed_pages: int = None,
        milvus_collection_name: str = None,
        vector_count: int = None,
        language: str = None,
        author: str = None,
        subject: str = None,
        metadata_json: dict = None,
        processing_config: dict = None,
        processed_at: datetime = None,
        permissions: List[str] = None,
        document_type: str = 'common'
    ) -> Document:
        """문서 생성"""
        try:
            document = Document(
                document_id=document_id,
                document_name=document_name,
                original_filename=original_filename,
                file_key=file_key,
                file_size=file_size,
                file_type=file_type,
                file_extension=file_extension,
                user_id=user_id,
                upload_path=upload_path,
                status=status,
                error_message=error_message,
                is_public=is_public,
                # 새로운 optional 필드들
                file_hash=file_hash,
                total_pages=total_pages,
                processed_pages=processed_pages,
                milvus_collection_name=milvus_collection_name,
                vector_count=vector_count,
                language=language,
                author=author,
                subject=subject,
                metadata_json=metadata_json,
                processing_config=processing_config,
                processed_at=processed_at,
                permissions=permissions,
                document_type=document_type,
                create_dt=datetime.now()
            )
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            return document
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 생성 실패: {str(e)}")
            raise
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """문서 조회"""
        try:
            return self.db.query(Document).filter(Document.document_id == document_id).first()
        except Exception as e:
            logger.error(f"문서 조회 실패: {str(e)}")
            raise
    
    def get_user_documents(self, user_id: str) -> List[Document]:
        """사용자의 문서 목록 조회"""
        try:
            return self.db.query(Document)\
                .filter(Document.user_id == user_id)\
                .filter(Document.is_deleted == False)\
                .order_by(desc(Document.create_dt))\
                .all()
        except Exception as e:
            logger.error(f"사용자 문서 목록 조회 실패: {str(e)}")
            raise
    
    def search_documents(self, user_id: str, search_term: str) -> List[Document]:
        """문서 검색"""
        try:
            return self.db.query(Document)\
                .filter(Document.user_id == user_id)\
                .filter(Document.is_deleted == False)\
                .filter(
                    (Document.document_name.contains(search_term)) |
                    (Document.original_filename.contains(search_term))
                )\
                .order_by(desc(Document.create_dt))\
                .all()
        except Exception as e:
            logger.error(f"문서 검색 실패: {str(e)}")
            raise
    
    def update_document(self, document_id: str, **kwargs) -> bool:
        """문서 정보 업데이트"""
        try:
            document = self.get_document(document_id)
            if document:
                for key, value in kwargs.items():
                    if hasattr(document, key):
                        setattr(document, key, value)
                document.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 업데이트 실패: {str(e)}")
            raise
    
    def update_document_status(self, document_id: str, status: str, error_message: str = None) -> bool:
        """문서 상태 업데이트"""
        try:
            document = self.get_document(document_id)
            if document:
                document.status = status
                if error_message:
                    document.error_message = error_message
                if status == 'completed':
                    document.processed_at = datetime.now()
                document.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 상태 업데이트 실패: {str(e)}")
            raise
    
    def update_processing_info(self, document_id: str, **kwargs) -> bool:
        """문서 처리 정보 업데이트 (페이지, 벡터 정보 등)"""
        try:
            document = self.get_document(document_id)
            if document:
                # 허용된 필드들만 업데이트
                allowed_fields = {
                    'total_pages', 'processed_pages', 'milvus_collection_name', 
                    'vector_count', 'language', 'author', 'subject', 
                    'metadata_json', 'processing_config', 'processed_at', 'permissions', 'document_type'
                }
                
                for key, value in kwargs.items():
                    if key in allowed_fields and hasattr(document, key):
                        setattr(document, key, value)
                
                document.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 처리 정보 업데이트 실패: {str(e)}")
            raise
    
    def find_document_by_hash(self, file_hash: str, status_filter: str = None) -> Optional[Document]:
        """파일 해시를 기반으로 기존 문서 검색 (중복 체크용)"""
        try:
            query = self.db.query(Document).filter(Document.file_hash == file_hash)
            if status_filter:
                query = query.filter(Document.status == status_filter)
            return query.first()
        except Exception as e:
            logger.error(f"해시 기반 문서 검색 실패: {str(e)}")
            raise
    
    def find_completed_document_by_hash(self, file_hash: str) -> Optional[Document]:
        """완료된 상태의 기존 문서 검색 (완전 중복 체크용)"""
        try:
            return self.db.query(Document)\
                .filter(Document.file_hash == file_hash)\
                .filter(Document.status == 'completed')\
                .filter(Document.is_deleted == False)\
                .first()
        except Exception as e:
            logger.error(f"완료된 문서 검색 실패: {str(e)}")
            raise
    
    def check_document_permission(self, document_id: str, required_permission: str) -> bool:
        """문서의 특정 권한 체크"""
        try:
            document = self.get_document(document_id)
            if not document:
                return False
            return document.has_permission(required_permission)
        except Exception as e:
            logger.error(f"문서 권한 체크 실패: {str(e)}")
            raise
    
    def check_document_permissions(self, document_id: str, required_permissions: List[str], require_all: bool = False) -> bool:
        """문서의 여러 권한 체크"""
        try:
            document = self.get_document(document_id)
            if not document:
                return False
            return document.has_permissions(required_permissions, require_all)
        except Exception as e:
            logger.error(f"문서 권한들 체크 실패: {str(e)}")
            raise
    
    def update_document_permissions(self, document_id: str, permissions: List[str]) -> bool:
        """문서 권한 업데이트"""
        try:
            document = self.get_document(document_id)
            if document:
                document.permissions = permissions
                document.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 권한 업데이트 실패: {str(e)}")
            raise
    
    def add_document_permission(self, document_id: str, permission: str) -> bool:
        """문서에 권한 추가"""
        try:
            document = self.get_document(document_id)
            if document:
                if not document.permissions:
                    document.permissions = []
                if permission not in document.permissions:
                    document.permissions = document.permissions + [permission]  # 새 리스트 생성
                    document.updated_at = datetime.now()
                    self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 권한 추가 실패: {str(e)}")
            raise
    
    def remove_document_permission(self, document_id: str, permission: str) -> bool:
        """문서에서 권한 제거"""
        try:
            document = self.get_document(document_id)
            if document and document.permissions and permission in document.permissions:
                new_permissions = [p for p in document.permissions if p != permission]
                document.permissions = new_permissions
                document.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 권한 제거 실패: {str(e)}")
            raise
    
    def get_documents_with_permission(self, user_id: str, required_permission: str) -> List[Document]:
        """특정 권한을 가진 사용자 문서 목록 조회"""
        try:
            return self.db.query(Document)\
                .filter(Document.user_id == user_id)\
                .filter(Document.is_deleted == False)\
                .filter(Document.permissions.contains([required_permission]))\
                .order_by(desc(Document.create_dt))\
                .all()
        except Exception as e:
            logger.error(f"권한별 문서 목록 조회 실패: {str(e)}")
            raise
    
    def get_documents_by_type(self, user_id: str, document_type: str) -> List[Document]:
        """특정 문서 타입의 사용자 문서 목록 조회"""
        try:
            return self.db.query(Document)\
                .filter(Document.user_id == user_id)\
                .filter(Document.document_type == document_type)\
                .filter(Document.is_deleted == False)\
                .order_by(desc(Document.create_dt))\
                .all()
        except Exception as e:
            logger.error(f"타입별 문서 목록 조회 실패: {str(e)}")
            raise
    
    def update_document_type(self, document_id: str, document_type: str) -> bool:
        """문서 타입 업데이트"""
        try:
            # 유효한 타입 검증
            if document_type not in Document.VALID_DOCUMENT_TYPES:
                raise ValueError(f"유효하지 않은 문서 타입: {document_type}. 허용된 타입: {Document.VALID_DOCUMENT_TYPES}")
            
            document = self.get_document(document_id)
            if document:
                document.document_type = document_type
                document.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 타입 업데이트 실패: {str(e)}")
            raise
    
    def get_document_type_stats(self, user_id: str) -> Dict[str, int]:
        """사용자의 문서 타입별 통계 조회"""
        try:
            results = self.db.query(
                Document.document_type,
                func.count(Document.document_id).label('count')
            ).filter(
                Document.user_id == user_id,
                Document.is_deleted == False
            ).group_by(Document.document_type).all()
            
            # 기본 타입들로 초기화
            stats = {'common': 0, 'type1': 0, 'type2': 0}
            
            # 실제 데이터로 업데이트
            for doc_type, count in results:
                if doc_type in stats:
                    stats[doc_type] = count
                else:
                    stats[doc_type or 'common'] = count  # None인 경우 common으로 처리
            
            return stats
        except Exception as e:
            logger.error(f"문서 타입별 통계 조회 실패: {str(e)}")
            raise
    
    def delete_document(self, document_id: str) -> bool:
        """문서 삭제 (소프트 삭제)"""
        try:
            document = self.get_document(document_id)
            if document:
                document.is_deleted = True
                document.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 삭제 실패: {str(e)}")
            raise


class DocumentChunkCRUD:
    """DocumentChunk 관련 CRUD 작업을 처리하는 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        page_number: int,
        chunk_type: str,
        content: str = None,
        image_description: str = None,
        image_path: str = None,
        milvus_id: str = None,
        embedding_model: str = None,
        vector_dimension: int = None,
        char_count: int = None,
        word_count: int = None,
        language: str = None,
        metadata_json: dict = None
    ) -> DocumentChunk:
        """문서 청크 생성"""
        try:
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                page_number=page_number,
                chunk_type=chunk_type,
                content=content,
                image_description=image_description,
                image_path=image_path,
                milvus_id=milvus_id,
                embedding_model=embedding_model,
                vector_dimension=vector_dimension,
                char_count=char_count,
                word_count=word_count,
                language=language,
                metadata_json=metadata_json
            )
            self.db.add(chunk)
            self.db.commit()
            self.db.refresh(chunk)
            return chunk
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 청크 생성 실패: {str(e)}")
            raise
    
    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """청크 조회"""
        try:
            return self.db.query(DocumentChunk).filter(DocumentChunk.chunk_id == chunk_id).first()
        except Exception as e:
            logger.error(f"청크 조회 실패: {str(e)}")
            raise
    
    def get_document_chunks(self, doc_id: str) -> List[DocumentChunk]:
        """문서의 모든 청크 조회"""
        try:
            return self.db.query(DocumentChunk)\
                .filter(DocumentChunk.doc_id == doc_id)\
                .order_by(DocumentChunk.page_number)\
                .all()
        except Exception as e:
            logger.error(f"문서 청크 목록 조회 실패: {str(e)}")
            raise
    
    def update_chunk(self, chunk_id: str, **kwargs) -> bool:
        """청크 정보 업데이트"""
        try:
            chunk = self.get_chunk(chunk_id)
            if chunk:
                for key, value in kwargs.items():
                    if hasattr(chunk, key):
                        setattr(chunk, key, value)
                chunk.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"청크 업데이트 실패: {str(e)}")
            raise
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """청크 삭제"""
        try:
            chunk = self.get_chunk(chunk_id)
            if chunk:
                self.db.delete(chunk)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"청크 삭제 실패: {str(e)}")
            raise
    
    def delete_document_chunks(self, doc_id: str) -> int:
        """문서의 모든 청크 삭제"""
        try:
            deleted_count = self.db.query(DocumentChunk)\
                .filter(DocumentChunk.doc_id == doc_id)\
                .delete()
            self.db.commit()
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"문서 청크 일괄 삭제 실패: {str(e)}")
            raise


class ProcessingJobCRUD:
    """ProcessingJob 관련 CRUD 작업을 처리하는 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_job(
        self,
        job_id: str,
        doc_id: str,
        job_type: str,
        flow_run_id: str = None,
        total_steps: int = 0
    ) -> ProcessingJob:
        """처리 작업 생성"""
        try:
            job = ProcessingJob(
                job_id=job_id,
                doc_id=doc_id,
                job_type=job_type,
                flow_run_id=flow_run_id,
                total_steps=total_steps
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            return job
        except Exception as e:
            self.db.rollback()
            logger.error(f"처리 작업 생성 실패: {str(e)}")
            raise
    
    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """작업 조회"""
        try:
            return self.db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
        except Exception as e:
            logger.error(f"작업 조회 실패: {str(e)}")
            raise
    
    def update_job_status(self, job_id: str, status: str, **kwargs) -> bool:
        """작업 상태 업데이트"""
        try:
            job = self.get_job(job_id)
            if job:
                job.status = status
                if status == 'completed':
                    job.completed_at = datetime.now()
                
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                
                job.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"작업 상태 업데이트 실패: {str(e)}")
            raise
    
    def get_document_jobs(self, doc_id: str) -> List[ProcessingJob]:
        """문서의 모든 작업 조회"""
        try:
            return self.db.query(ProcessingJob)\
                .filter(ProcessingJob.doc_id == doc_id)\
                .order_by(desc(ProcessingJob.started_at))\
                .all()
        except Exception as e:
            logger.error(f"문서 작업 목록 조회 실패: {str(e)}")
            raise
