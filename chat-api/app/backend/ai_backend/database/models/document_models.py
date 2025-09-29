# _*_ coding: utf-8 _*_
"""
Document Models - 공통 모듈 사용
"""

# 공통 모듈에서 모델들을 import
from shared_core import Document, DocumentChunk, ProcessingJob

# 기존 코드와의 호환성을 위한 별칭들
__all__ = [
    "Document",
    "DocumentChunk", 
    "ProcessingJob"
]