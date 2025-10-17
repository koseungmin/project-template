# shared/file_manager/schema/file_object.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from ...response.base import CommonResponse


class FileObjectData(BaseModel):
    """파일 응답 데이터 모델"""

    id: str
    comp_id: str
    category: str
    relative_path: Optional[str]
    absolute_path: Optional[str]
    storage_type: Optional[str]
    filename: str
    size: int
    created_at: datetime

    class Config:
        from_attributes = True


class FileObjectStreamBase(BaseModel):
    filename: str
    mime_type: str


class FileObjectDownloadData(FileObjectStreamBase):
    download_path: str


class FileObjectStreamData(FileObjectStreamBase):
    bytes: bytes


class FileObjectListData(BaseModel):
    items: List[FileObjectData]
    count: int
    total: int


class FileObjectResponse(CommonResponse):
    data: FileObjectData


class FileObjectListResponse(CommonResponse):
    """Response model for listing files in storage"""

    data: FileObjectListData = Field(description="파일 목록")


class FileObjectMoveRequest(BaseModel):
    tenant_id: Optional[str] = Field(
        None, description="DB tenant ID, None이면 Common DB 조회"
    )
    file_id: Optional[str] = Field(
        None, description="원본 파일 ID (값이 있으면 category 파라미터 무시)"
    )
    category: Optional[str] = Field(None, description="원본 파일 카테고리")
