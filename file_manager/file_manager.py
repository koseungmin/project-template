import asyncio
import logging
import mimetypes
import os
import tempfile
import time
import unicodedata
import uuid
from threading import Lock
from typing import Optional

import aiofiles
from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..core.config import get_common_settings
from ..response.base import ResponseCode
from ..response.exceptions import ServiceException
from ..security.security import CurrentUser
from .schema.file_object import *
from .service.file_object import FileObjectService
from .storage.storage_factory import StorageFactory

settings = get_common_settings()


class FileManager:
    """
    A singleton class for managing file storage in multiple cloud providers or local storage.

    This class provides functionalities for:
    - Uploading files to cloud storage or local storage
    - Retrieving files by ID
    - Downloading and deleting files
    - Generating pre-signed URLs for cloud storage access
    """

    _instance = None
    _lock = Lock()
    _resource_lock = Lock()

    def __init__(self):
        """Ensures only one instance of FileManager exists (Singleton pattern)."""
        if not hasattr(self, "_initialized"):
            self._initialize()
            self._initialized = True

        self.logger = logging.getLogger(__name__)

    @classmethod
    def get_instance(cls):
        """
        Retrieves the singleton instance of FileManager.

        Returns:
            FileManager: A singleton instance of the class.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _initialize(self):
        """
        Initializes the file storage system by:
        - Determining if cloud storage should be used
        - Selecting the appropriate storage provider
        - Validating required environment variables
        """
        self.use_cloud_storage = settings.USE_CLOUD_STORAGE
        self.cloud_storage_provider = settings.CLOUD_STORAGE_TYPE
        self.required_env_vars = self._get_required_env_vars()
        self._validate_env_vars()

    def _get_storage(self, comp_id: str):
        """
        Get storage instance based on configuration and company code.

        Args:
            comp_id (str): Company code

        Returns:
            Storage instance or None for local storage
        """
        if not self.use_cloud_storage:
            return None

        return StorageFactory.get_storage(comp_id)

    def _get_required_env_vars(self):
        """
        Returns a list of required environment variables based on the selected cloud provider.

        Returns:
            list: A list of required environment variable names.
        """
        cloud_env_vars = {
            "azure": [
                "AZURE_STORAGE_CONNECTION_STRING",
                "AZURE_FILE_SHARE_NAME",
                "AZURE_STORAGE_CONTAINER",
            ],
            "aws": ["AWS_ACCESS_KEY", "AWS_SECRET_KEY", "AWS_S3_BUCKET"],
            "gcp": ["GCP_BUCKET"],
        }

        # NCP/Naver 프로바이더인 경우 동적으로 환경변수 생성
        if self.cloud_storage_provider in ["ncp", "naver"]:
            return self._get_ncp_required_env_vars()

        return cloud_env_vars.get(self.cloud_storage_provider, [])

    def _get_ncp_required_env_vars(self):
        """
        Returns a list of required NCP environment variables for all supported companies.

        Returns:
            list: A list of required NCP environment variable names.
        """
        try:
            supported_companies = settings.get_supported_companies()

            required_vars = []

            # 공통 환경변수들
            common_vars = [
                "NCP_OBJECT_STORAGE_ENDPOINT",
                "NCP_OBJECT_STORAGE_REGION",
                "NCP_OBJECT_STORAGE_BUCKET_NAME_PREFIX",
                "COMPANIES",  # 지원되는 회사 목록
            ]
            required_vars.extend(common_vars)

            # 각 회사별 환경변수들 (정규화된 회사 코드 사용)
            for company in supported_companies:
                normalized_company = settings.normalize_company_code(company)
                company_vars = [
                    f"NCP_OBJECT_STORAGE_{normalized_company}_ACCESS_KEY",
                    f"NCP_OBJECT_STORAGE_{normalized_company}_SECRET_KEY",
                ]
                required_vars.extend(company_vars)

            return required_vars

        except Exception as e:
            # 설정을 가져올 수 없는 경우 기본 환경변수 반환
            return [
                "NCP_OBJECT_STORAGE_ENDPOINT",
                "NCP_OBJECT_STORAGE_REGION",
                "NCP_OBJECT_STORAGE_BUCKET_NAME_PREFIX",
                "COMPANIES",
            ]

    def _validate_env_vars(self):
        """
        Validates that all required environment variables are set.

        Raises:
            ServiceException: If any required environment variables are missing.
        """
        if not self.use_cloud_storage:
            return
        missing_vars = [var for var in self.required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ServiceException(
                response_code=ResponseCode.INVALID_CONFIG_ERROR,
                e=EnvironmentError(
                    f"Missing required environment variables: {', '.join(missing_vars)}"
                ),
            )

    @staticmethod
    def _get_root_directory(compid: str, is_common: bool) -> str:
        """
        Determines the root directory for file storage.

        The root directory is selected based on the environment (`DEV`, `STG`, `PRD`) and
        whether the file is common/shared or user-specific.

        Args:
            compid (str): The company ID associated with the file.
            is_common (bool): Whether the file is shared across multiple users.

        Returns:
            str: The absolute root directory path.
        """
        root = os.getenv("DATA_PATH", "/data")
        if not is_common:
            if compid:
                root = f"/{compid.upper()}/data"

        return root.replace(
            os.path.sep, "/"
        )  # 경로 구분자 정리 (Windows => Linux/Unix)

    @staticmethod
    def _generate_file_id() -> str:
        """
        Generates a unique 32-character UUID for use as a file identifier.

        Returns:
            str: A UUID string without hyphens.
        """
        return uuid.uuid4().hex

    @staticmethod
    def _normalize_filename(filename: str) -> str:
        """
        Normalizes file names to prevent encoding issues and maintain consistency.

        Args:
            filename (str): The original file name.

        Returns:
            str: The normalized file name.
        """
        filename = unicodedata.normalize("NFC", filename)  # Unicode 정규화
        # filename = re.sub(
        #     r"[^\w\-_\.]", "_", filename
        # )  # 특수문자 제거 (영문, 숫자, `_`, `-`, `.`만 허용)
        return filename

    @staticmethod
    def _get_absolute_path(
        root_dir: str,
        relative_path: str,
        file_id: str,
    ) -> str:
        """
        Constructs the absolute file path and ensures necessary directories exist.

        Args:
            root_dir (str): The root directory for file storage.
            relative_path (str): The relative path within the storage system.
            file_id (str): The unique file identifier.

        Returns:
            str: The absolute file path.
        """
        if not relative_path:
            relative_path = ""

        if file_id:
            absolute_path = os.path.join(root_dir, relative_path, file_id)
        else:
            absolute_path = os.path.join(root_dir, relative_path)

        # 부모 디렉토리 확인 및 생성
        parent_dir = os.path.dirname(absolute_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        return absolute_path.replace(
            os.path.sep, "/"
        )  # 경로 구분자 정리 (Windows => Linux/Unix)

    @staticmethod
    def _get_relative_path(
        category: str = None, relative_path: str = None, file_id: str = None
    ) -> str:
        """
        Constructs a relative file path.

        Ensures that only valid directory paths are included, removing any unnecessary slashes.

        Args:
            category (Optional[str]): The category of the file.
            relative_path (Optional[str]): The user-specified relative path.
            file_id (Optional[str]): The unique file identifier.

        Returns:
            str: A sanitized relative path.
        """
        if not category:
            category = ""

        if not relative_path:
            relative_path = ""

        if not file_id:
            file_id = ""

        result_path = relative_path or ""
        if os.path.isabs(result_path):
            result_path = os.path.relpath(result_path, "/")

        # 파일명이 실제로 포함되어 있는지 확인
        # 확장자가 있는 경우에만 파일명으로 간주하고 디렉토리만 추출
        if result_path and "." in os.path.basename(result_path):
            # 파일명이 포함된 경우에만 디렉토리만 유지
            result_path = os.path.dirname(result_path)

        # 마지막 문자가 '/' ('\') 인 경우, 제거
        if result_path.endswith(os.path.sep):
            result_path = result_path[:-1]

        result_path = os.path.join(category, result_path, file_id)
        return result_path.replace(
            os.path.sep, "/"
        )  # 경로 구분자 정리 (Windows => Linux/Unix)

    @staticmethod
    def _get_blob_name(
        relative_path: str = None,
        comp_id: str = None,
    ) -> str:
        """
        Constructs a blob name for cloud storage.

        Args:
            relative_path (Optional[str]): The user-specified relative path (already include category and file_id).
            comp_id (Optional[str]): The company ID.

        Returns:
            str: A sanitized blob name with format 'prc/common/{relative_path}' for COMMON
                 or 'prc/{relative_path}' for other companies
        """
        if not relative_path:
            relative_path = ""

        if os.path.isabs(relative_path):
            relative_path = os.path.relpath(relative_path, "/")

        # 마지막 문자가 '/' ('\') 인 경우, 제거
        if relative_path.endswith(os.path.sep):
            relative_path = relative_path[:-1]

        # comp_id가 COMMON인 경우 특별한 blob_name 생성
        if comp_id == "COMMON":
            blob_name = os.path.join("prc", "common", relative_path)
        else:
            blob_name = os.path.join("prc", relative_path)

        return blob_name.replace(
            os.path.sep, "/"
        )  # 경로 구분자 정리 (Windows => Linux/Unix)

    @staticmethod
    async def upload(
        *,
        db: Session,
        user: Optional[CurrentUser] = None,
        is_common: Optional[bool] = False,
        is_private: Optional[bool] = False,
        category: str,
        relative_path: Optional[str] = None,
        file: UploadFile,
        storage_type: Optional[str] = None,
        commit_flag: Optional[bool] = True,
    ) -> FileObjectData:
        """
        Uploads a file to cloud storage or local storage.

        Args:
            db (Session): The database session.
            user (CurrentUser, optional): The user uploading the file.
            is_common (bool, optional): Whether the file is shared across all users.
            is_private (bool, optional): Whether the file is private to the user.
            category (str): The category of the file.
            relative_path (str, optional): The relative path where the file will be stored.
            file (UploadFile): The uploaded file object.
            storage_type (str, optional): Storage type
            commit_flag (bool, optional): Whether to commit the transaction.

        Returns:
            FileObjectData: Metadata about the uploaded file.
        """
        if not category:
            raise ServiceException(
                response_code=ResponseCode.INVALID_PARAMETER,
                e=ValueError("category can not be None"),
            )

        instance = FileManager.get_instance()
        comp_id = "COMMON" if is_common else user.compid
        file_id = instance._generate_file_id()
        filename = instance._normalize_filename(file.filename)
        relative_path = instance._get_relative_path(category, relative_path, file_id)
        root_dir = instance._get_root_directory(comp_id, is_common)
        absolute_path = instance._get_absolute_path(
            root_dir,
            relative_path,
            None,
        )

        # Determine whether to use cloud storage
        use_cloud = storage_type is not None and instance.use_cloud_storage

        # Save file locally first
        with open(absolute_path, "wb") as f:
            file_data = await file.read()
            f.write(file_data)

        size = len(file_data)

        # Upload to cloud storage if needed
        if use_cloud:
            storage = instance._get_storage(comp_id)
            if storage:
                try:
                    # Generate blob_name using the new method
                    blob_name = instance._get_blob_name(relative_path, comp_id)

                    # Reset file pointer to beginning before upload
                    await file.seek(0)

                    # Upload to cloud storage
                    storage.upload(
                        absolute_path,
                        blob_name,
                    )

                    # Update absolute_path to blob_name for cloud storage
                    absolute_path = blob_name

                    try:
                        # Remove local file after successful cloud upload
                        local_path = instance._get_absolute_path(
                            root_dir, relative_path, None
                        )
                        os.remove(local_path)
                        instance.logger.info(
                            f"Local file removed after cloud upload: {local_path}"
                        )
                    except OSError as e:
                        # Log the error but don't fail the upload process
                        instance.logger.warning(
                            f"Failed to remove local file after cloud upload: {local_path}, error: {e}"
                        )

                except Exception as e:
                    # If cloud upload fails, keep the local file and log the error
                    instance.logger.error(f"Failed to upload to cloud storage: {e}")
                    raise ServiceException(
                        response_code=ResponseCode.CLOUD_STORAGE_ERROR,
                        e=e,
                    )

        file_object = FileObjectService.create_file(
            db,
            file_id,
            user.id if user else -1,
            is_private,
            comp_id,
            category,
            relative_path,
            absolute_path,
            storage_type,
            filename,
            size,
        )

        db.flush()
        db.refresh(file_object)

        if commit_flag:
            db.commit()

        return FileObjectData(
            id=file_id,
            comp_id=comp_id,
            category=category,
            relative_path=relative_path,
            absolute_path=absolute_path,
            filename=filename,
            size=size,
            storage_type=storage_type,
            created_at=datetime.now(),
        )

    @staticmethod
    def get_list(
        *,
        db: Session,
        user: Optional[CurrentUser] = None,
        category: Optional[str] = None,
        relative_path: Optional[str] = None,
        absolute_path: Optional[str] = None,
        storage_type: Optional[str] = None,
        filename: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
    ):
        """
        Retrieves a list of files based on filtering criteria.

        If `absolute_path` is provided, it takes precedence over other filtering parameters.

        Args:
            db (Session): The database session.
            user (Optional[CurrentUser]): The user requesting the file list.
            category (Optional[str]): The file category (e.g., 'proposal', 'etc').
            relative_path (Optional[str]): The relative path of the files.
            absolute_path (Optional[str]): The absolute path of the files (overrides other parameters).
            storage_type (Optional[str]): The storage type of the files.
            filename (Optional[str]): The filename (supports partial matches).
            offset (int, optional): The pagination offset. Defaults to 0.
            limit (int, optional): The number of records per page. Defaults to 10.

        Returns:
            Tuple[List[FileObjectData], int]: A list of files and the total count of matching files.
        """
        if absolute_path:
            category = None
            relative_path = None
            filename = None

        files, total = FileObjectService.get_all(
            db,
            user.id if user else None,
            category,
            relative_path,
            absolute_path,
            storage_type,
            filename,
            offset,
            limit,
        )
        return files, total

    @staticmethod
    def get_file_object(
        *,
        db: Session,
        user: Optional[CurrentUser] = None,
        file_id: str,
    ) -> FileObjectData:
        instance = FileManager.get_instance()
        with instance._resource_lock:
            file_object = FileObjectService.get_file_by_id(db, file_id)
            if not file_object:
                raise ServiceException(ResponseCode.FILE_NOT_FOUND)

            if file_object.is_private:
                if not user:
                    raise ServiceException(ResponseCode.FORBIDDEN)
                if file_object.user_id != user.id:
                    raise ServiceException(ResponseCode.FORBIDDEN)

        return FileObjectData(
            id=file_object.id,
            comp_id=file_object.comp_id,
            category=file_object.category,
            relative_path=file_object.relative_path,
            absolute_path=file_object.absolute_path,
            storage_type=file_object.storage_type,
            filename=file_object.filename,
            size=file_object.size,
            created_at=file_object.created_at,
        )

    @staticmethod
    def download(
        *,
        db: Session,
        user: Optional[CurrentUser] = None,
        file_id: str,
    ) -> FileObjectDownloadData:
        """
        Downloads a file from cloud storage or local storage.

        Args:
            db (Session): The database session.
            user (CurrentUser, optional): The user requesting the file.
            file_id (str): The unique identifier of the file.

        Returns:
            FileObjectDownloadData: Information about the downloaded file.

        Raises:
            ServiceException: If the file is not found or the user lacks permissions.
        """
        instance = FileManager.get_instance()
        with instance._resource_lock:
            file_object = FileObjectService.get_file_by_id(db, file_id)
            if not file_object:
                raise ServiceException(ResponseCode.FILE_NOT_FOUND)

            if file_object.is_private:
                if not user:
                    raise ServiceException(ResponseCode.FORBIDDEN)
                if file_object.user_id != user.id:
                    raise ServiceException(ResponseCode.FORBIDDEN)

            # Determine whether to use cloud storage
            use_cloud = (
                file_object.storage_type is not None and instance.use_cloud_storage
            )

            # 파일 다운로드 경로 결정
            temp_dir = tempfile.gettempdir()
            download_path = os.path.join(temp_dir, file_object.filename)

            if use_cloud:
                storage = instance._get_storage(file_object.comp_id)
                if storage:
                    storage.download(
                        file_object.absolute_path,
                        download_path,
                    )
                else:
                    raise ServiceException(
                        response_code=ResponseCode.INVALID_CONFIG_ERROR,
                        e=ValueError("Cloud storage not available"),
                    )
            else:
                # 로컬 파일 시스템에서 복사
                if os.path.exists(file_object.absolute_path):
                    with open(file_object.absolute_path, "rb") as src, open(
                        download_path, "wb"
                    ) as dst:
                        dst.write(src.read())
                else:
                    raise ServiceException(
                        response_code=ResponseCode.FILE_NOT_FOUND,
                        e=FileNotFoundError(
                            f"File not found: {file_object.absolute_path}"
                        ),
                    )

            content_type, _ = mimetypes.guess_type(file_object.filename)
            return FileObjectDownloadData(
                download_path=download_path,
                filename=file_object.filename,
                mime_type=(
                    content_type if content_type else "application/octet-stream"
                ),
            )

    @staticmethod
    async def adownload(
        *,
        db: Session,
        user: Optional[CurrentUser] = None,
        file_id: str,
    ) -> FileObjectDownloadData:
        """
        Asynchronously downloads a file from cloud storage or local storage.

        Args:
            db (Session): The database session.
            user (CurrentUser, optional): The user requesting the file.
            file_id (str): The unique identifier of the file.

        Returns:
            FileObjectDownloadData: Information about the downloaded file.

        Raises:
            ServiceException: If the file is not found or the user lacks permissions.
        """
        instance = FileManager.get_instance()
        with instance._resource_lock:
            file_object = FileObjectService.get_file_by_id(db, file_id)
            if not file_object:
                raise ServiceException(ResponseCode.FILE_NOT_FOUND)

            if file_object.is_private:
                if not user:
                    raise ServiceException(ResponseCode.FORBIDDEN)
                if file_object.user_id != user.id:
                    raise ServiceException(ResponseCode.FORBIDDEN)

            # Determine whether to use cloud storage
            use_cloud = (
                file_object.storage_type is not None and instance.use_cloud_storage
            )

            # 파일 다운로드 경로 결정
            temp_dir = tempfile.gettempdir()
            download_path = os.path.join(temp_dir, file_object.filename)

            if use_cloud:
                storage = instance._get_storage(file_object.comp_id)
                if storage:
                    # TODO : storage download 비동기 처리 필요
                    storage.download(
                        file_object.absolute_path,
                        download_path,
                    )
                else:
                    raise ServiceException(
                        response_code=ResponseCode.INVALID_CONFIG_ERROR,
                        e=ValueError("Cloud storage not available"),
                    )
            else:
                # 로컬 파일 시스템에서 비동기 복사
                if os.path.exists(file_object.absolute_path):
                    async with aiofiles.open(
                        file_object.absolute_path, "rb"
                    ) as src, aiofiles.open(download_path, "wb") as dst:
                        await dst.write(await src.read())
                else:
                    raise ServiceException(
                        response_code=ResponseCode.FILE_NOT_FOUND,
                        e=FileNotFoundError(
                            f"File not found: {file_object.absolute_path}"
                        ),
                    )

            content_type, _ = mimetypes.guess_type(file_object.filename)
            return FileObjectDownloadData(
                download_path=download_path,
                filename=file_object.filename,
                mime_type=(
                    content_type if content_type else "application/octet-stream"
                ),
            )

    @staticmethod
    async def move_storage(
        *, db: Session, file_id: str, relative_path: str = None
    ) -> Optional[FileObjectData]:
        """
        다른 스토리지에 저장된 파일을 현재 사용 중인 스토리지로 이동하고 FileObject 데이터 업데이트
        Args:
            file_id: 원본 파일 ID
        """

        def convert_category(
            category: str, relative_path: str, file_id: str
        ) -> tuple[str, str]:
            """
            old category로 저장된 경우 new category, relative_path로 변환
            """
            from shared.file_manager.schema.file_category import FileCategory

            path_list = relative_path.split("/")
            if category == "bpupload":
                if len(path_list) < 3:
                    return None, None
                converted_category = FileCategory.BATCH_BP_UPLOAD
                converted_path = f"{converted_category}/{path_list[1]}/{file_id}"
            elif category == "bid":
                converted_category = FileCategory.BID_RFP
                converted_path = f"{converted_category}/{relative_path}"
            elif category == "proposal":
                converted_category = FileCategory.BID_EVAL_FORM
                converted_path = f"{converted_category}/{relative_path}"
            elif category == "proposal-eval":
                if len(path_list) < 3:
                    return None, None
                converted_category = FileCategory.BID_PROPOSAL_EVAL
                converted_path = f"{converted_category}/{path_list[1]}/{file_id}"
            elif category == "transaction":
                if len(path_list) < 3:
                    return None, None
                converted_category = FileCategory.BPSOURCE_TRANSACTION
                converted_path = f"{converted_category}/{path_list[1]}/{file_id}"
            elif category == FileCategory.BID_RFP_EXAMPLE:
                converted_category = category
                converted_path = f"{converted_category}/{relative_path}"
            else:
                return None, None

            return converted_category, converted_path

        instance = FileManager.get_instance()
        if not instance.use_cloud_storage or not instance.cloud_storage_provider:
            raise ServiceException(
                ResponseCode.NOT_DEFINED, "not support cloud storage"
            )

        file_object = FileObjectService.get_file_by_id(db, file_id)
        if not file_object or not os.path.exists(file_object.absolute_path):
            raise ServiceException(
                ResponseCode.FILE_NOT_FOUND,
                f"file not found: {file_id}",
            )
        if file_object.storage_type == instance.cloud_storage_provider:
            raise ServiceException(
                ResponseCode.INVALID_DATA_STATUS,
                f"file is already on the current storage: {file_object.absolute_path}",
            )

        if relative_path:
            file_object.relative_path = f"{relative_path}/{file_id}"
        category, relative_path = convert_category(
            file_object.category, file_object.relative_path, file_id
        )
        if not category:
            raise ServiceException(
                ResponseCode.INVALID_DATA_STATUS,
                f"unsupported file: {file_object.absolute_path}",
            )

        storage = instance._get_storage(file_object.comp_id)
        if storage:
            blob_name = instance._get_blob_name(relative_path, file_object.comp_id)

            # Upload to cloud storage
            storage.upload(
                file_object.absolute_path,
                blob_name,
            )

            # update file info
            file_object = FileObjectService.update_file(
                db,
                file_id,
                {
                    "category": category,
                    "relative_path": relative_path,
                    "absolute_path": blob_name,
                    "storage_type": instance.cloud_storage_provider,
                },
            )
            db.commit()

            return FileObjectData(
                id=file_id,
                comp_id=file_object.comp_id,
                category=category,
                relative_path=relative_path,
                absolute_path=blob_name,
                filename=file_object.filename,
                size=file_object.size,
                storage_type=instance.cloud_storage_provider,
                created_at=file_object.created_at,
            )
        else:
            return None

    @staticmethod
    def delete(
        *,
        db: Session,
        user: Optional[CurrentUser] = None,
        file_id: str,
    ) -> None:
        """
        Deletes a file from cloud storage or local storage.

        This method performs a logical delete by marking the file as deleted in the database.
        If the file exists in storage, it will be physically removed.

        Args:
            db (Session): The database session.
            user (Optional[CurrentUser]): The user performing the delete action.
            file_id (str): The unique identifier of the file to be deleted.

        Raises:
            ServiceException: If the file does not exist or the user does not have permission to delete it.
        """
        instance = FileManager.get_instance()
        with instance._resource_lock:
            file_object = FileObjectService.get_file_by_id(db, file_id)
            if not file_object:
                raise ServiceException(ResponseCode.FILE_NOT_FOUND)

            if file_object.is_private:
                if not user:
                    raise ServiceException(ResponseCode.FORBIDDEN)
                if file_object.user_id != user.id:
                    raise ServiceException(ResponseCode.FORBIDDEN)

            # Determine whether to use cloud storage
            use_cloud = (
                file_object.storage_type is not None and instance.use_cloud_storage
            )

            if use_cloud and file_object.storage_type:
                storage = instance._get_storage(file_object.comp_id)
                if storage:
                    storage.delete(file_object.absolute_path)
            else:
                # 로컬 파일 시스템에서 삭제
                if os.path.exists(file_object.absolute_path):
                    os.remove(file_object.absolute_path)
                # else:
                #     raise ServiceException(
                #         response_code=ResponseCode.FILE_NOT_FOUND,
                #         e=FileNotFoundError(
                #             f"File not found: {file_object.absolute_path}"
                #         ),
                #     )

            result = FileObjectService.delete_file(db, file_id, user.id)
            db.commit()
            return result

    @staticmethod
    def get_as_bytes(
        *,
        db: Session,
        user: Optional[CurrentUser] = None,
        file_id: str,
    ) -> FileObjectStreamData:
        """
        Retrieves a file as a byte stream.

        This method fetches the file contents either from cloud storage or local storage,
        returning it as raw bytes.

        Args:
            db (Session): The database session.
            user (Optional[CurrentUser]): The user requesting the file.
            file_id (str): The unique identifier of the file.

        Returns:
            FileObjectStreamData: A data object containing the file content as bytes.

        Raises:
            ServiceException: If the file does not exist or the user lacks permission to access it.
        """
        instance = FileManager.get_instance()
        with instance._resource_lock:
            file_object = FileObjectService.get_file_by_id(db, file_id)
            if not file_object:
                raise ServiceException(ResponseCode.FILE_NOT_FOUND)

            if file_object.is_private:
                if not user:
                    raise ServiceException(ResponseCode.FORBIDDEN)
                if file_object.user_id != user.id:
                    raise ServiceException(ResponseCode.FORBIDDEN)

            # Determine whether to use cloud storage
            use_cloud = (
                file_object.storage_type is not None and instance.use_cloud_storage
            )

            if use_cloud:
                storage = instance._get_storage(file_object.comp_id)
                if storage:
                    bytes_data = storage.get_blob_as_bytes(file_object.absolute_path)
                else:
                    raise ServiceException(
                        response_code=ResponseCode.INVALID_CONFIG_ERROR,
                        e=ValueError("Cloud storage not available"),
                    )
            else:
                # 로컬 파일 시스템에서 파일 읽기
                if os.path.exists(file_object.absolute_path):
                    with open(file_object.absolute_path, "rb") as f:
                        bytes_data = f.read()
                else:
                    raise ServiceException(
                        response_code=ResponseCode.FILE_NOT_FOUND,
                        e=FileNotFoundError(
                            f"File not found: {file_object.absolute_path}"
                        ),
                    )

            content_type, _ = mimetypes.guess_type(file_object.filename)
            return FileObjectStreamData(
                bytes=bytes_data,
                filename=file_object.filename,
                mime_type=(
                    content_type if content_type else "application/octet-stream"
                ),
            )

    # @staticmethod
    # def get_pre_signed_url(
    #     *,
    #     db: Session,
    #     user: Optional[CurrentUser] = None,
    #     file_id: str,
    #     expiry_hours: int = 1,
    #     storage_type: Optional[str] = None,
    # ) -> str:
    #     """
    #     Generates a pre-signed URL for the specified file.

    #     This allows users to access the file via a temporary, signed URL without needing direct authentication.

    #     Args:
    #         db (Session): The database session.
    #         user (Optional[CurrentUser]): The user requesting the pre-signed URL.
    #         file_id (str): The unique identifier of the file.
    #         expiry_hours (int, optional): The expiration time for the URL in hours. Defaults to 1.
    #         storage_type (str, optional): Storage type

    #     Returns:
    #         str: The pre-signed URL for the file.

    #     Raises:
    #         ServiceException: If the file does not exist or the user lacks permission to access it.
    #     """
    #     instance = FileManager.get_instance()
    #     with instance._resource_lock:
    #         file_object = FileObjectService.get_file_by_id(db, file_id)
    #         if not file_object:
    #             raise ServiceException(ResponseCode.FILE_NOT_FOUND)

    #         if file_object.is_private:
    #             if not user:
    #                 raise ServiceException(ResponseCode.FORBIDDEN)
    #             if file_object.user_id != user.id:
    #                 raise ServiceException(ResponseCode.FORBIDDEN)

    #         # Determine whether to use cloud storage
    #         use_cloud = storage_type is not None and instance.use_cloud_storage

    #         if not use_cloud:
    #             raise ServiceException(
    #                 response_code=ResponseCode.INVALID_CONFIG_ERROR,
    #                 e=ValueError(
    #                     f"Pre-signed URLs are only available for cloud storage."
    #                 ),
    #             )

    #         storage = instance._get_storage(file_object.comp_id)
    #         if not storage:
    #             raise ServiceException(
    #                 response_code=ResponseCode.INVALID_CONFIG_ERROR,
    #                 e=ValueError("Cloud storage not available"),
    #             )

    #         return storage.get_blob_url(
    #             instance._get_relative_path(
    #                 file_object.category, file_object.relative_path, file_id
    #             ),
    #             expiry_hours,
    #         )

    # @staticmethod
    # def rename(
    #     *,
    #     db: Session,
    #     user: Optional[CurrentUser] = None,
    #     file_id: str,
    #     new_filename: str,
    #     is_force: bool = False,
    # ) -> FileObjectData:
    #     """
    #     Renames an existing file's filename in the database without changing its actual storage path.

    #     Args:
    #         db (Session): The database session.
    #         user (Optional[CurrentUser]): The user requesting the file rename.
    #         file_id (str): The unique identifier of the file to rename.
    #         new_filename (str): The new filename. **Must include an extension**.
    #         is_force (bool, optional): If True, allows renaming even if the extensions differ. Defaults to `False`.

    #     Returns:
    #         FileObjectData: The updated file metadata with the new filename.

    #     Raises:
    #         ServiceException:
    #             - If the file does not exist.
    #             - If `new_filename` does not include an extension.
    #             - If the file extensions differ and `is_force=False`.
    #     """
    #     if not new_filename or "." not in new_filename:
    #         raise ServiceException(
    #             response_code=ResponseCode.INVALID_PARAMETER,
    #             e=ValueError("New filename must include a valid extension."),
    #         )

    #     instance = FileManager.get_instance()

    #     with instance._resource_lock:
    #         # 파일 정보 조회
    #         file_object = FileObjectService.get_file_by_id(db, file_id)
    #         if not file_object:
    #             raise ServiceException(ResponseCode.FILE_NOT_FOUND)

    #         # 접근 권한 확인
    #         if file_object.is_private:
    #             if not user:
    #                 raise ServiceException(ResponseCode.FORBIDDEN)
    #             if file_object.user_id != user.id:
    #                 raise ServiceException(ResponseCode.FORBIDDEN)

    #         old_filename = file_object.filename
    #         old_extension = os.path.splitext(old_filename)[1].lower()
    #         new_extension = os.path.splitext(new_filename)[1].lower()

    #         # 확장자 변경 확인
    #         if old_extension and new_extension and old_extension != new_extension:
    #             if not is_force:
    #                 raise ServiceException(
    #                     response_code=ResponseCode.INVALID_PARAMETER,
    #                     e=ValueError(
    #                         f"File extension mismatch: '{old_filename}' -> '{new_filename}'. Use is_force=True to override."
    #                     ),
    #                 )

    #         # 데이터베이스에서 파일명만 변경 (저장된 파일의 경로는 변경하지 않음)
    #         file_object.filename = new_filename
    #         db.commit()

    #     return FileObjectData(
    #         id=file_object.id,
    #         comp_id=file_object.comp_id,
    #         category=file_object.category,
    #         relative_path=file_object.relative_path,
    #         absolute_path=file_object.absolute_path,  # 실제 저장된 파일 경로는 변경 없음
    #         storage_type=file_object.storage_type,
    #         filename=file_object.filename,  # 변경된 파일명만 반영
    #         size=file_object.size,
    #         created_at=file_object.created_at,
    #     )
