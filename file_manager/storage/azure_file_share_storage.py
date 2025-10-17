# shared/file_manager/storage/azure_file_share_storage.py
import os
from datetime import datetime, timedelta
from typing import List, Optional

from azure.storage.fileshare import ShareDirectoryClient, ShareServiceClient

from .storage_base import StorageBase


class AzureFileShareStorage(StorageBase):
    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        share_name = os.getenv("AZURE_FILE_SHARE_NAME")  # File Share 이름
        self.client = ShareServiceClient.from_connection_string(connection_string)
        self.share = self.client.get_share_client(share_name)

    def _get_directory_client(self, path: str) -> ShareDirectoryClient:
        """디렉토리 클라이언트를 반환"""
        return self.share.get_directory_client(path)

    def upload(self, file_path: str, blob_name: str) -> str:
        """Azure File Share에 파일을 업로드"""
        directory_path = os.path.dirname(blob_name)
        file_name = os.path.basename(blob_name)

        directory_client = self._get_directory_client(directory_path)
        file_client = directory_client.get_file_client(file_name)

        with open(file_path, "rb") as file_data:
            file_client.upload_file(file_data)

        return blob_name

    def download(self, blob_name: str, download_path: str) -> None:
        """Azure File Share에서 파일 다운로드"""
        directory_path = os.path.dirname(blob_name)
        file_name = os.path.basename(blob_name)

        directory_client = self._get_directory_client(directory_path)
        file_client = directory_client.get_file_client(file_name)

        with open(download_path, "wb") as download_file:
            stream = file_client.download_file()
            download_file.write(stream.readall())

    def delete(self, blob_name: str) -> None:
        """Azure File Share에서 파일 삭제"""
        directory_path = os.path.dirname(blob_name)
        file_name = os.path.basename(blob_name)

        directory_client = self._get_directory_client(directory_path)
        file_client = directory_client.get_file_client(file_name)

        file_client.delete_file()

    def get_file_list(self, path: Optional[str] = None) -> List[str]:
        """Azure File Share 내 특정 디렉토리의 파일 목록을 반환"""
        directory_client = self._get_directory_client(path if path else "")
        return [file["name"] for file in directory_client.list_directories_and_files()]

    def get_blob_as_bytes(self, blob_name: str) -> bytes:
        """Azure File Share에서 파일을 바이트로 가져오기"""
        directory_path = os.path.dirname(blob_name)
        file_name = os.path.basename(blob_name)

        directory_client = self._get_directory_client(directory_path)
        file_client = directory_client.get_file_client(file_name)

        return file_client.download_file().readall()

    def get_blob_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Azure File Share에서 공유 URL을 생성 (SAS 토큰)"""
        directory_path = os.path.dirname(blob_name)
        file_name = os.path.basename(blob_name)

        sas_token = self.client.generate_share_sas(
            account_name=self.client.account_name,
            share_name=self.share.share_name,
            permission="r",
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
        )

        return f"https://{self.client.account_name}.file.core.windows.net/{self.share.share_name}/{directory_path}/{file_name}?{sas_token}"
