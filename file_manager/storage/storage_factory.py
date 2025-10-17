# shared/file_manager/storage/storage_factory.py
import os
from typing import Type

from ...core.config import get_common_settings
from ...response.base import ResponseCode
from ...response.exceptions import ServiceException
from ..schema.cloud_storage_provider import CloudStorageProvider
from .aws_blob_storage import AWSBlobStorage
from .azure_blob_storage import AzureBlobStorage
from .azure_file_share_storage import AzureFileShareStorage
from .gcp_blob_storage import GCPBlobStorage
from .ncp_storage import NCPBlobStorage
from .storage_base import StorageBase

settings = get_common_settings()


class StorageFactory:
    """
    Factory class to instantiate the correct cloud storage handler based on environment variable.
    """

    @staticmethod
    def get_storage(comp_id: str) -> StorageBase:
        """
        Returns an instance of the appropriate storage class based on CLOUD_PROVIDER.
        """
        provider = settings.CLOUD_STORAGE_TYPE

        try:
            cloud_provider = CloudStorageProvider(provider)
        except ValueError:
            raise ServiceException(
                response_code=ResponseCode.INVALID_CONFIG_ERROR,
                e=ValueError(
                    f"Unsupported CLOUD_STORAGE_PROVIDER: {provider}. Supported: {list(CloudStorageProvider)}"
                ),
            )

        if cloud_provider == CloudStorageProvider.AZURE:
            # Azure 스토리지 타입(blob or file_share) 확인
            storage_type = os.getenv("AZURE_STORAGE_TYPE", "file_share").lower()
            if storage_type == "blob":
                return AzureBlobStorage()
            return AzureFileShareStorage()

        storage_classes: dict[CloudStorageProvider, Type] = {
            CloudStorageProvider.AWS: AWSBlobStorage,
            CloudStorageProvider.NCP: NCPBlobStorage,
            CloudStorageProvider.GCP: GCPBlobStorage,
        }

        storage_class = storage_classes.get(cloud_provider)
        if not storage_class:
            raise ServiceException(
                response_code=ResponseCode.INVALID_CONFIG_ERROR,
                e=ValueError(f"Invalid storage provider: {provider}"),
            )
        return storage_class(comp_id)
