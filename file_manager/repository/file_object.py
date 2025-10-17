from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..model.file_object import FileObject


class FileObjectRepository:
    """File 테이블의 데이터 관리 (CRUD)"""

    @staticmethod
    def create(session: Session, blob_file: FileObject) -> FileObject:
        """새로운 파일 정보를 생성"""
        session.add(blob_file)
        # session.commit()
        session.flush()
        session.refresh(blob_file)
        return blob_file

    @staticmethod
    def get_by_id(session: Session, file_id: str) -> Optional[FileObject]:
        """파일 ID로 파일 정보 조회"""
        return (
            session.query(FileObject)
            .filter(FileObject.id == file_id, FileObject.is_deleted == False)
            .first()
        )

    @staticmethod
    def get_all(
        session: Session,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        relative_path: Optional[str] = None,
        absolute_path: Optional[str] = None,
        storage_type: Optional[str] = None,
        filename: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
    ):
        """모든 파일 조회 (옵션: 특정 유저 ID 기준)"""
        query = session.query(FileObject).filter(FileObject.is_deleted == False)

        # **개인 파일 접근 제한: user_id가 없으면 개인 파일 제외**
        # if user_id:
        #     query = query.filter(
        #         (FileObject.is_private == False) | (FileObject.user_id == user_id)
        #     )
        # else:
        #     query = query.filter(FileObject.is_private == False)

        if category:
            query = query.filter(FileObject.category == category)
        if relative_path:
            query = query.filter(FileObject.relative_path.like(f"%{relative_path}%"))
        if absolute_path:
            query = query.filter(FileObject.absolute_path.like(f"{absolute_path}%"))
        if filename:
            query = query.filter(FileObject.filename.like(f"%{filename}%"))
        if storage_type:
            query = query.filter(FileObject.storage_type == storage_type)
        total = query.count()
        files = query.offset(offset).limit(limit).all()
        return files, total

    @staticmethod
    def update(
        session: Session, file_id: str, update_data: dict
    ) -> Optional[FileObject]:
        """파일 정보 업데이트"""
        blob_file = session.query(FileObject).filter(FileObject.id == file_id).first()
        if not blob_file:
            return None

        for key, value in update_data.items():
            setattr(blob_file, key, value)

        blob_file.updated_at = func.now()
        session.flush()
        return blob_file

    @staticmethod
    def soft_delete(session: Session, file_id: str, deleted_by: int) -> bool:
        """파일 논리 삭제"""
        blob_file = session.query(FileObject).filter(FileObject.id == file_id).first()
        if not blob_file:
            return False

        blob_file.is_deleted = True
        blob_file.deleted_at = func.now()
        blob_file.deleted_by = deleted_by
        # session.commit()
        return True
