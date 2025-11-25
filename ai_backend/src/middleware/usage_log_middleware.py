# _*_ coding: utf-8 _*_
"""API Usage Log middleware for tracking user activity."""
import json
import logging
import time
from typing import Optional

from fastapi import Request, Response
from src.config import settings
from src.database.base import Database
from src.database.crud.usage_log_crud import UsageLogCRUD
from src.utils.uuid_gen import gen
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)


class UsageLogMiddleware(BaseHTTPMiddleware):
    """API 사용 이력 추적 미들웨어"""
    
    # 제외할 경로 목록 (로그인, 헬스체크 등)
    EXCLUDE_PATHS = [
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
        "/v1/auth/login",  # 로그인 API 제외 (인증 전이므로 user_id가 없음)
    ]
    
    # 민감 정보 필드 (요청 본문에서 제외)
    SENSITIVE_FIELDS = [
        "password",
        "secret",
        "token",
        "api_key",
        "access_token",
        "refresh_token",
        "authorization",
    ]
    
    def __init__(self, app, database: Database):
        super().__init__(app)
        self.database = database
    
    def _is_excluded_path(self, path: str) -> bool:
        """제외할 경로인지 확인"""
        for excluded_path in self.EXCLUDE_PATHS:
            if path.startswith(excluded_path):
                return True
        return False
    
    def _extract_service_name(self, path: str) -> Optional[str]:
        """엔드포인트에서 서비스명 추출"""
        # /v1/chat/messages -> chat
        # /v1/document/upload -> document
        # /v1/user/profile -> user
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            # v1 다음의 부분이 서비스명
            if parts[0] == "v1" and len(parts) > 1:
                return parts[1]
        return None
    
    def _sanitize_body(self, body: dict) -> dict:
        """민감 정보를 제거한 요청 본문 생성"""
        if not isinstance(body, dict):
            return body
        
        sanitized = {}
        for key, value in body.items():
            key_lower = key.lower()
            # 민감 정보 필드인 경우 제외
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_body(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_body(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """클라이언트 IP 주소 추출"""
        # X-Forwarded-For 헤더 확인 (프록시 환경)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 직접 연결인 경우
        if request.client:
            return request.client.host
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        """요청 처리 및 사용 이력 기록"""
        start_time = time.time()
        
        # 제외 경로인 경우 통과
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # 토큰 인증이 꺼져있으면 user 정보 없이 로그 저장하지 않음
        # user_id는 무조건 토큰에서만 가져옴 (auth_middleware에서 이미 검증된 payload 사용)
        user_id = None
        employee_id = None
        
        # JWT 인증이 활성화되어 있고, auth_middleware에서 검증된 payload가 있는 경우만
        if settings.jwt_enabled and hasattr(request.state, "jwt_payload"):
            jwt_payload = request.state.jwt_payload
            user_id = jwt_payload.get("user_id") or jwt_payload.get("sub") or jwt_payload.get("id")
            employee_id = jwt_payload.get("employee_id")
        
        # 토큰 인증이 꺼져있거나 user_id가 없으면 로그 저장하지 않음
        if not settings.jwt_enabled or not user_id:
            return await call_next(request)
        
        # 요청 정보 수집
        endpoint = request.url.path
        method = request.method
        service_name = self._extract_service_name(endpoint)
        
        # 쿼리 파라미터
        request_params = dict(request.query_params) if request.query_params else None
        
        # 요청 본문 (POST, PUT, PATCH만)
        # 주의: FastAPI에서 요청 본문은 한 번만 읽을 수 있으므로,
        # 미들웨어에서 읽으면 실제 라우터에서 읽을 수 없게 됩니다.
        # 따라서 요청 본문은 기록하지 않거나, 스트림을 복원해야 합니다.
        # 여기서는 쿼리 파라미터와 엔드포인트 정보만 기록합니다.
        request_body = None
        # 요청 본문 기록은 선택사항으로, 필요시 별도 처리 필요
        
        # 클라이언트 정보
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        
        # 응답 처리
        response_status = 200
        error_message = None
        
        try:
            response = await call_next(request)
            response_status = response.status_code
            
            # 응답 시간 계산
            response_time = int((time.time() - start_time) * 1000)  # 밀리초
            
            # 사용 이력 기록 (비동기로 처리하여 응답 지연 최소화)
            try:
                with self.database.session() as db:
                    log_crud = UsageLogCRUD(db)
                    log_crud.create_log(
                        log_id=gen(),
                        user_id=user_id,
                        employee_id=employee_id,
                        endpoint=endpoint,
                        method=method,
                        service_name=service_name,
                        request_params=request_params,
                        request_body=request_body,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        response_status=response_status,
                        response_time=response_time,
                        error_message=error_message,
                    )
            except Exception as e:
                # 이력 기록 실패는 로깅만 하고 응답에는 영향 없음
                logger.error(f"사용 이력 기록 실패: {str(e)}")
            
            return response
            
        except Exception as e:
            # 예외 발생 시
            response_status = 500
            error_message = str(e)
            response_time = int((time.time() - start_time) * 1000)
            
            # 에러 이력 기록
            try:
                with self.database.session() as db:
                    log_crud = UsageLogCRUD(db)
                    log_crud.create_log(
                        log_id=gen(),
                        user_id=user_id,
                        employee_id=employee_id,
                        endpoint=endpoint,
                        method=method,
                        service_name=service_name,
                        request_params=request_params,
                        request_body=request_body,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        response_status=response_status,
                        response_time=response_time,
                        error_message=error_message,
                    )
            except Exception as log_error:
                logger.error(f"에러 이력 기록 실패: {str(log_error)}")
            
            # 예외 재발생
            raise

