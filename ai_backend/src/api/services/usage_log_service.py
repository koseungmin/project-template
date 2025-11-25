# _*_ coding: utf-8 _*_
"""Usage Log Service for managing API usage logs."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session
from src.database.crud.usage_log_crud import UsageLogCRUD
from src.types.response.exceptions import HandledException
from src.types.response.response_code import ResponseCode

logger = logging.getLogger(__name__)


class UsageLogService:
    """API 사용 이력 서비스"""
    
    def __init__(self, db: Session):
        if db is None:
            raise ValueError("Database session is required")
        
        self.db = db
        self.usage_log_crud = UsageLogCRUD(db)
    
    def get_logs(
        self,
        user_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        service_name: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """사용 이력 조회"""
        try:
            logs = self.usage_log_crud.get_logs(
                user_id=user_id,
                employee_id=employee_id,
                service_name=service_name,
                endpoint=endpoint,
                method=method,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset,
            )
            
            total_count = self.usage_log_crud.get_logs_count(
                user_id=user_id,
                employee_id=employee_id,
                service_name=service_name,
                endpoint=endpoint,
                method=method,
                start_date=start_date,
                end_date=end_date,
            )
            
            return {
                "logs": [
                    {
                        "log_id": log.log_id,
                        "user_id": log.user_id,
                        "employee_id": log.employee_id,
                        "endpoint": log.endpoint,
                        "method": log.method,
                        "service_name": log.service_name,
                        "request_params": log.request_params,
                        "request_body": log.request_body,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "response_status": log.response_status,
                        "response_time": log.response_time,
                        "error_message": log.error_message,
                        "create_dt": log.create_dt.isoformat() if log.create_dt else None,
                    }
                    for log in logs
                ],
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            }
        except HandledException:
            raise
        except Exception as e:
            logger.exception("사용 이력 조회 중 오류가 발생했습니다.")
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def get_service_statistics(
        self,
        days: int = 7,
    ) -> List[Dict]:
        """서비스별 사용 통계"""
        try:
            end_date = datetime.now(ZoneInfo("Asia/Seoul"))
            start_date = end_date - timedelta(days=days)
            
            return self.usage_log_crud.get_service_statistics(
                start_date=start_date,
                end_date=end_date,
            )
        except HandledException:
            raise
        except Exception as e:
            logger.exception("서비스 통계 조회 중 오류가 발생했습니다.")
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def get_user_statistics(
        self,
        days: int = 7,
        limit: int = 10,
    ) -> List[Dict]:
        """사용자별 사용 통계"""
        try:
            end_date = datetime.now(ZoneInfo("Asia/Seoul"))
            start_date = end_date - timedelta(days=days)
            
            return self.usage_log_crud.get_user_statistics(
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        except HandledException:
            raise
        except Exception as e:
            logger.exception("사용자 통계 조회 중 오류가 발생했습니다.")
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)

