import logging
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from shared.core.config import get_common_settings

from .storage_base import StorageBase


class NCPBlobStorage(StorageBase):
    def __init__(self, company_code: str):
        """
        Initialize Naver Cloud Storage client

        Args:
            company_code: Company code (e.g., 'SKCC', 'SKT', 'SKTB')
        """
        self.settings = get_common_settings()
        self.company_code = company_code
        self.logger = logging.getLogger(__name__)

        try:
            config = self.settings.get_ncp_config(company_code)
            self.bucket_name = config.bucket_name

            self.client = boto3.client(
                "s3",
                aws_access_key_id=config.access_key,
                aws_secret_access_key=config.secret_key,
                endpoint_url=config.endpoint_url,
                region_name=config.region_name,
            )

            # Test connection by checking if bucket exists
            self._ensure_bucket_exists()

        except Exception as e:
            self.logger.error(f"Failed to initialize Naver Cloud Storage client: {e}")
            raise

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if it doesn't"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            self.logger.info(f"Bucket {self.bucket_name} exists and is accessible")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                self.logger.error(f"Bucket {self.bucket_name} does not exist")
                raise RuntimeError(
                    f"Bucket {self.bucket_name} does not exist. Please create it first."
                )
            elif error_code == "403":
                self.logger.error(f"Access denied to bucket {self.bucket_name}")
                raise RuntimeError(
                    f"Access denied to bucket {self.bucket_name}. Check your credentials."
                )
            else:
                self.logger.error(f"Error checking bucket {self.bucket_name}: {e}")
                raise

    def upload(self, file_path: str, blob_name: str) -> str:
        """Upload a file to Naver Cloud Storage

        Args:
            file_path: Local file path to upload
            blob_name: Object key name in the bucket

        Returns:
            Success message

        Raises:
            RuntimeError: If upload fails
        """
        try:
            self.client.upload_file(file_path, self.bucket_name, blob_name)
            self.logger.info(f"Successfully uploaded {file_path} to {blob_name}")
            return f"Uploaded {blob_name} to Naver Cloud Storage."
        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except NoCredentialsError:
            error_msg = "Missing or invalid Naver Cloud credentials"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except ClientError as e:
            error_msg = f"Failed to upload {file_path} to {blob_name}: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def download(self, blob_name: str, download_path: str) -> None:
        """Download a file from Naver Cloud Storage

        Args:
            blob_name: Object key name in the bucket
            download_path: Local path to save the downloaded file

        Raises:
            RuntimeError: If download fails
        """
        try:
            self.client.download_file(self.bucket_name, blob_name, download_path)
            self.logger.info(f"Successfully downloaded {blob_name} to {download_path}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                error_msg = f"Object {blob_name} not found in bucket {self.bucket_name}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                error_msg = f"Failed to download {blob_name}: {e}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Failed to download {blob_name}: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def delete(self, blob_name: str) -> None:
        """Delete a file from Naver Cloud Storage

        Args:
            blob_name: Object key name in the bucket

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=blob_name)
            self.logger.info(f"Successfully deleted {blob_name}")
        except ClientError as e:
            error_msg = f"Failed to delete {blob_name}: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def get_file_list(self, path: Optional[str] = None) -> List[str]:
        """Lists all files in the Naver Cloud Storage bucket within a specific path.

        Args:
            path: Optional prefix to filter objects

        Returns:
            List of object keys

        Raises:
            RuntimeError: If listing fails
        """
        try:
            objects = []
            paginator = self.client.get_paginator("list_objects_v2")

            # Set up pagination parameters
            page_params = {"Bucket": self.bucket_name}
            if path:
                page_params["Prefix"] = path

            # Iterate through all pages
            for page in paginator.paginate(**page_params):
                if "Contents" in page:
                    objects.extend([obj["Key"] for obj in page["Contents"]])

            self.logger.info(f"Found {len(objects)} objects with prefix '{path or ''}'")
            return objects

        except ClientError as e:
            error_msg = f"Failed to list objects: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def get_blob_as_bytes(self, blob_name: str) -> bytes:
        """Retrieves a blob as a byte stream.

        Args:
            blob_name: Object key name in the bucket

        Returns:
            File content as bytes

        Raises:
            RuntimeError: If retrieval fails
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=blob_name)
            content = response["Body"].read()
            self.logger.info(
                f"Successfully retrieved {blob_name} as bytes ({len(content)} bytes)"
            )
            return content
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                error_msg = f"Object {blob_name} not found in bucket {self.bucket_name}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                error_msg = f"Failed to retrieve {blob_name}: {e}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

    def get_blob_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Generates a presigned URL for the given blob.

        Args:
            blob_name: Object key name in the bucket
            expiry_hours: URL expiration time in hours (default: 1)

        Returns:
            Presigned URL

        Raises:
            RuntimeError: If URL generation fails
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": blob_name},
                ExpiresIn=expiry_hours * 3600,
            )
            self.logger.info(
                f"Generated presigned URL for {blob_name} (expires in {expiry_hours} hours)"
            )
            return url
        except NoCredentialsError:
            error_msg = "Missing or invalid Naver Cloud credentials"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except ClientError as e:
            error_msg = f"Failed to generate presigned URL for {blob_name}: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
