# shared/file_manager/storage/storage_base.py
from abc import ABC, abstractmethod
from typing import List, Optional


class StorageBase(ABC):
    """
    Abstract base class for Storage implementations.
    """

    @abstractmethod
    def upload(self, file_path: str, blob_name: str) -> str:
        """Uploads a file to the storage."""
        pass

    @abstractmethod
    def download(self, blob_name: str, download_path: str) -> None:
        """Downloads a file from the storage."""
        pass

    @abstractmethod
    def delete(self, blob_name: str) -> None:
        """Deletes a file from the storage."""
        pass

    @abstractmethod
    def get_file_list(self, path: Optional[str] = None) -> List[str]:
        """Lists all files in the storage container."""
        pass

    @abstractmethod
    def get_blob_as_bytes(self, blob_name: str) -> bytes:
        """Retrieves a file as a byte stream."""
        pass

    @abstractmethod
    def get_blob_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Generates a signed URL for the that expires in a given time."""
        pass
