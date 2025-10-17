# shared/file_manager/storage/aws_blob_storage.py
import os
from typing import List, Optional

import boto3

from .storage_base import StorageBase

"""테스트안해봄(추후실제필요시디버깅필요)"""


class AWSBlobStorage(StorageBase):
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
        )
        self.bucket_name = os.getenv("AWS_S3_BUCKET")

    def upload(self, file_path: str, blob_name: str) -> str:
        self.s3.upload_file(file_path, self.bucket_name, blob_name)
        return f"Uploaded {blob_name} to AWS S3."

    def download(self, blob_name: str, download_path: str) -> None:
        self.s3.download_file(self.bucket_name, blob_name, download_path)

    def delete(self, blob_name: str) -> None:
        self.s3.delete_object(Bucket=self.bucket_name, Key=blob_name)

    def get_file_list(self, path: Optional[str] = None) -> List[str]:
        """Lists all files in the AWS S3 bucket within a specific path."""
        response = self.s3.list_objects_v2(
            Bucket=self.bucket_name, Prefix=path if path else ""
        )
        return (
            [obj["Key"] for obj in response.get("Contents", [])]
            if "Contents" in response
            else []
        )

    def get_blob_as_bytes(self, blob_name: str) -> bytes:
        """Retrieves a blob as a byte stream."""
        response = self.s3.get_object(Bucket=self.bucket, Key=blob_name)
        return response["Body"].read()

    def get_blob_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Generates a presigned URL for the given blob."""
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": blob_name},
            ExpiresIn=expiry_hours * 3600,
        )
