# shared/file_manager/storage/gcp_blob_storage.py
import os
from datetime import timedelta
from typing import List, Optional

from google.cloud import storage

from .storage_base import StorageBase

"""테스트안해봄(추후실제필요시디버깅필요)"""


class GCPBlobStorage(StorageBase):
    def __init__(self):
        self.client = storage.Client()
        self.bucket_name = os.getenv("GCP_BUCKET")
        self.bucket = self.client.bucket(self.bucket_name)

    def upload(self, file_path: str, blob_name: str) -> str:
        blob = self.bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        return f"Uploaded {blob_name} to Google Cloud Storage."

    def download(self, blob_name: str, download_path: str) -> None:
        blob = self.bucket.blob(blob_name)
        blob.download_to_filename(download_path)

    def delete(self, blob_name: str) -> None:
        blob = self.bucket.blob(blob_name)
        blob.delete()

    def get_file_list(self, path: Optional[str] = None) -> List[str]:
        """Lists all files in Google Cloud Storage bucket under the specified path."""
        blobs = self.bucket.list_blobs(prefix=path if path else "")
        return [blob.name for blob in blobs]

    def get_blob_as_bytes(self, blob_name: str) -> bytes:
        """Retrieves a blob as a byte stream."""
        blob = self.bucket.blob(blob_name)
        return blob.download_as_bytes()

    def get_blob_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Generates a signed URL for the given blob."""
        blob = self.bucket.blob(blob_name)
        url = blob.generate_signed_url(expiration=timedelta(hours=expiry_hours))
        return url
