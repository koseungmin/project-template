#!/usr/bin/env python3
"""
환경 변수 관리 모듈
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# .env 파일 로드
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

class Config:
    """환경 변수 관리 클래스"""
    
    # Azure OpenAI - GPT Vision (Chat Completions)
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")  # GPT Vision용
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")  # GPT-4 Vision 배포 이름
    
    # Azure OpenAI - Embeddings (별도 API 버전)
    AZURE_OPENAI_EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", "2023-12-01-preview")  # 임베딩용
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")  # 임베딩 모델 배포 이름
    
    # Milvus Lite (파일 기반)
    MILVUS_URI = os.getenv("MILVUS_URI", "./milvus_lite.db")  # 파일 기반 DB
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")  # 백업용 (Docker 사용시)
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")     # 백업용 (Docker 사용시)
    MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "document_vectors")
    USE_MILVUS_LITE = os.getenv("USE_MILVUS_LITE", "true").lower() == "true"
    
    # PostgreSQL 데이터베이스 설정
    DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "chat_db")
    DATABASE_USERNAME = os.getenv("DATABASE_USERNAME", "postgres")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")
    DATABASE_ECHO = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    # PostgreSQL 연결 문자열
    @property
    def postgres_url(self) -> str:
        """PostgreSQL 연결 URL 생성"""
        if not self.DATABASE_PASSWORD:
            return f"postgresql://{self.DATABASE_USERNAME}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        return f"postgresql://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
    
    # 파일 경로 설정
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./extracted_image"))
    
    # 기본 문서 및 폴더 경로 설정 
    DEFAULT_DOCUMENT_PATH = os.getenv("DEFAULT_DOCUMENT_PATH", "./test.pdf")
    DEFAULT_FOLDER_PATH = os.getenv("DEFAULT_FOLDER_PATH", "./uploads")
    TEST_DOCUMENT_PATH = os.getenv("TEST_DOCUMENT_PATH", "./test.pdf") 
    TEST_FOLDER_PATH = os.getenv("TEST_FOLDER_PATH", "./test_folder")
    
    # 문서 처리 제한 설정
    MAX_PAGES_TO_PROCESS = int(os.getenv("MAX_PAGES_TO_PROCESS", "10"))
    
    @classmethod
    def validate_config(cls) -> bool:
        """필수 환경 변수 검증"""
        required_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_KEY",
            "AZURE_OPENAI_DEPLOYMENT_NAME",  # GPT-4 Vision
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"  # 임베딩 모델
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
            print(f"📝 .env 파일을 확인하고 다음 변수들을 설정해주세요:")
            for var in missing_vars:
                if "DEPLOYMENT" in var:
                    print(f"   - {var}: Azure Portal에서 배포한 모델의 이름")
                else:
                    print(f"   - {var}")
            return False
        
        print("✅ 모든 필수 환경 변수가 설정되었습니다.")
        return True
    
    @classmethod
    def print_config(cls):
        """설정된 환경 변수 출력 (보안상 값은 마스킹)"""
        print(" 현재 환경 변수 설정:")
        config_vars = [
            "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY", 
            "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT_NAME",  # GPT Vision
            "AZURE_OPENAI_EMBEDDING_API_VERSION", "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",  # 임베딩
            "MILVUS_URI", "MILVUS_COLLECTION_NAME", "OUTPUT_DIR"
        ]
        
        for var in config_vars:
            value = getattr(cls, var)
            if "KEY" in var and value:
                masked_value = value[:8] + "*" * (len(value) - 8) if len(value) > 8 else "*" * len(value)
                print(f"   {var}: {masked_value}")
            else:
                print(f"   {var}: {value}")

# 전역 설정 인스턴스
config = Config()
