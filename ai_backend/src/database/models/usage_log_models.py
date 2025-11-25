# _*_ coding: utf-8 _*_
"""API Usage Log models for tracking user activity."""
from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.sql.expression import func
from src.database.base import Base

__all__ = [
    "APIUsageLog",
]


class APIUsageLog(Base):
    """API 사용 이력 테이블 - 사용자가 어떤 기능을 어떻게 사용했는지 추적"""
    __tablename__ = "API_USAGE_LOGS"
    
    log_id = Column('LOG_ID', String(50), primary_key=True)  # 로그 ID
    user_id = Column('USER_ID', String(50), nullable=True)  # 사용자 ID (인증되지 않은 경우 None)
    employee_id = Column('EMPLOYEE_ID', String(20), nullable=True)  # 사번
    endpoint = Column('ENDPOINT', String(500), nullable=False)  # API 엔드포인트
    method = Column('METHOD', String(10), nullable=False)  # HTTP 메서드 (GET, POST, PUT, DELETE)
    service_name = Column('SERVICE_NAME', String(100), nullable=True)  # 서비스명 (예: chat, document, user)
    
    # 요청 정보
    request_params = Column('REQUEST_PARAMS', JSON, nullable=True)  # 쿼리 파라미터
    request_body = Column('REQUEST_BODY', JSON, nullable=True)  # 요청 본문 (민감 정보 제외)
    ip_address = Column('IP_ADDRESS', String(50), nullable=True)  # 클라이언트 IP
    user_agent = Column('USER_AGENT', String(500), nullable=True)  # User-Agent
    
    # 응답 정보
    response_status = Column('RESPONSE_STATUS', Integer, nullable=False)  # HTTP 상태 코드
    response_time = Column('RESPONSE_TIME', Integer, nullable=True)  # 응답 시간 (밀리초)
    error_message = Column('ERROR_MESSAGE', Text, nullable=True)  # 에러 메시지 (에러 발생 시)
    
    # 메타 정보
    create_dt = Column('CREATE_DT', DateTime, nullable=False, server_default=func.now())  # 생성일시

