from typing import Optional

from sqlalchemy.orm import Session

from ..model.file_object import FileObject
from ..repository.file_object import FileObjectRepository
from ..schema.file_object import FileObjectData


class FileObjectService:
    """File 관련 서비스 로직을 처리"""

    @staticmethod
    def create_file(
        session: Session,
        id: str,
        user_id: int,
        is_private: bool,
        comp_id: int,
        category: str,
        relative_path: str,
        absolute_path: str,
        storage_type: Optional[str],
        filename: str,
        size: int,
    ) -> FileObject:
        """새로운 파일 생성"""
        new_file = FileObject(
            id=id,
            user_id=user_id,
            is_private=is_private,
            comp_id=comp_id,
            category=category,
            relative_path=relative_path,
            absolute_path=absolute_path,
            storage_type=storage_type,
            filename=filename,
            size=size,
        )
        return FileObjectRepository.create(session, new_file)

    @staticmethod
    def get_file_by_id(session: Session, file_id: str) -> Optional[FileObject]:
        """파일 ID로 조회"""
        return FileObjectRepository.get_by_id(session, file_id)

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
        """모든 파일 목록 조회"""
        files, total = FileObjectRepository.get_all(
            session,
            user_id,
            category,
            relative_path,
            absolute_path,
            storage_type,
            filename,
            offset,
            limit,
        )
        file_list = [
            FileObjectData(
                id=file.id,
                comp_id=file.comp_id,
                category=file.category,
                relative_path=file.relative_path,
                absolute_path=file.absolute_path,
                storage_type=file.storage_type,
                filename=file.filename,
                size=file.size,
                created_at=file.created_at,
            )
            for file in files
        ]
        return file_list, total

    @staticmethod
    def update_file(
        session: Session, file_id: str, update_data: dict
    ) -> Optional[FileObject]:
        """파일 정보 업데이트"""
        return FileObjectRepository.update(session, file_id, update_data)

    @staticmethod
    def delete_file(session: Session, file_id: str, deleted_by: int) -> bool:
        """파일 논리 삭제"""
        return FileObjectRepository.soft_delete(session, file_id, deleted_by)
