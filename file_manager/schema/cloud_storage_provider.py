# shared/file_manager/schema/cloud_storage_provider.py
from enum import Enum


class CloudStorageProvider(Enum):
    AWS = "aws"
    AZURE = "azure"
    NCP = "ncp"
    GCP = "gcp"
