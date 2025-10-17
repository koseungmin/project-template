# shared/file_manager/storage/azure_blob_storage.py
import os
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Optional

from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

from .storage_base import StorageBase


class AzureBlobStorage(StorageBase):
    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_STORAGE_CONTAINER")
        self.client = BlobServiceClient.from_connection_string(connection_string)
        self.container = self.client.get_container_client(container_name)

    def upload(self, file_path: str, blob_name: str) -> str:
        blob_client = self.container.get_blob_client(blob_name)
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data)
        return blob_name

    def download(self, blob_name: str, download_path: str) -> None:
        blob_client = self.container.get_blob_client(blob_name)
        with open(download_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())

    def delete(self, blob_name: str) -> None:
        encoded_blob_name = urllib.parse.quote(blob_name, safe=":/")  # URL 인코딩
        self.container.delete_blob(encoded_blob_name)

    def get_file_list(self, path: Optional[str] = None) -> List[str]:
        """Lists all files in the Azure Blob Storage container under the specified path."""
        # include = [tag.strip() for tag in path.split(",")] if tags else []
        return [blob.name for blob in self.container.list_blobs()]

    def get_blob_as_bytes(self, blob_name: str) -> bytes:
        """Retrieves a blob as a byte stream."""
        blob_client = self.container.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

    def get_blob_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Generates a signed URL (SAS token) for the given blob."""
        blob_client = self.container.get_blob_client(blob_name)
        sas_token = generate_blob_sas(
            account_name=self.container.account_name,
            container_name=self.container.container_name,
            blob_name=blob_name,
            account_key=self.container.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
        )
        return f"{blob_client.url}?{sas_token}"
