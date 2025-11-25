# _*_ coding: utf-8 _*_
"""Simple Pydantic Settings implementation for common_backend."""
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """통합 설정 클래스 - Pydantic Settings 방식 (암복호화 서비스용)"""
    
    # Application Configuration
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_locale: str = Field(default="en", env="APP_LOCALE")
    app_log_level: str = Field(default="info", env="APP_LOG_LEVEL")
    app_debug: bool = Field(default=False, env="APP_DEBUG")
    # FastAPI root_path 설정
    app_root_path: str = Field(default="", env="APP_ROOT_PATH")
    
    # Server Configuration
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8001, env="SERVER_PORT")
    server_debug: bool = Field(default=False, env="SERVER_DEBUG")
    server_reload: bool = Field(default=False, env="SERVER_RELOAD")
    server_log_level: str = Field(default="info", env="SERVER_LOG_LEVEL")
    
    # CORS Configuration
    cors_origins: str = Field(default="http://localhost:8001,file://", env="CORS_ORIGINS")
    
    # Logging Configuration
    log_to_file: bool = Field(default=False, env="LOG_TO_FILE")
    log_dir: str = Field(default="./logs", env="LOG_DIR")
    log_file: str = Field(default="app.log", env="LOG_FILE")
    log_rotation: str = Field(default="daily", env="LOG_ROTATION")
    log_retention_days: int = Field(default=30, env="LOG_RETENTION_DAYS")
    log_include_exc_info: bool = Field(default=True, env="LOG_INCLUDE_EXC_INFO")
    
    # JWT Configuration (클러스터 내부 서비스는 기본 비활성화)
    # 클러스터 내부에서만 호출하는 경우 CoreDNS + 네트워크 정책으로 보안 관리
    # 필요시에만 JWT_ENABLED=true로 활성화
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_secret_key: str = Field(default="change_me", env="JWT_SECRET_KEY")
    jwt_enabled: bool = Field(default=False, env="JWT_ENABLED")  # 기본 비활성화 (내부 서비스용)
    jwt_access_token_expires_minutes: int = Field(default=60, env="JWT_ACCESS_TOKEN_EXPIRES_MINUTES")
    jwt_issuer: Optional[str] = Field(default=None, env="JWT_ISSUER")
    jwt_exclude_paths: str = Field(default="/health,/docs,/openapi.json,/redoc", env="JWT_EXCLUDE_PATHS")
    
    # 암복호화 관련 설정 (사용자가 구현할 부분)
    # 예시: 암호화 알고리즘, 키 관리 등
    crypto_algorithm: str = Field(default="AES-256-GCM", env="CRYPTO_ALGORITHM")
    crypto_key_path: Optional[str] = Field(default=None, env="CRYPTO_KEY_PATH")
    
    def get_cors_origins(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def get_jwt_exclude_paths(self) -> List[str]:
        """JWT 제외 경로를 리스트로 반환"""
        if not self.jwt_exclude_paths:
            return []
        return [path.strip() for path in self.jwt_exclude_paths.split(",") if path.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# 전역 설정 인스턴스
settings = Settings()

