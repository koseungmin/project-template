# _*_ coding: utf-8 _*_
"""API Usage Log CRUD operations."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_, desc, func as sql_func, or_
from sqlalchemy.orm import Session
from src.database.models.usage_log_models import APIUsageLog
from src.types.response.exceptions import HandledException
from src.types.response.response_code import ResponseCode

logger = logging.getLogger(__name__)


class UsageLogCRUD:
    """API 사용 이력 CRUD 작업을 처리하는 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_log(
        self,
        log_id: str,
        endpoint: str,
        method: str,
        response_status: int,
        user_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        service_name: Optional[str] = None,
        request_params: Optional[dict] = None,
        request_body: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_time: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> APIUsageLog:
        """사용 이력 생성"""
        try:
            log = APIUsageLog(
                log_id=log_id,
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
                create_dt=datetime.now(ZoneInfo("Asia/Seoul")),
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            return log
        except Exception as e:
            self.db.rollback()
            logger.error(f"사용 이력 생성 실패: {str(e)}")
            # 이력 생성 실패는 로깅만 하고 예외를 발생시키지 않음 (메인 로직에 영향 없도록)
            return None
    
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
    ) -> List[APIUsageLog]:
        """사용 이력 조회 (필터링 지원)"""
        try:
            query = self.db.query(APIUsageLog)
            
            # 필터 조건 추가
            if user_id:
                query = query.filter(APIUsageLog.user_id == user_id)
            if employee_id:
                query = query.filter(APIUsageLog.employee_id == employee_id)
            if service_name:
                query = query.filter(APIUsageLog.service_name == service_name)
            if endpoint:
                query = query.filter(APIUsageLog.endpoint.like(f"%{endpoint}%"))
            if method:
                query = query.filter(APIUsageLog.method == method)
            if start_date:
                query = query.filter(APIUsageLog.create_dt >= start_date)
            if end_date:
                query = query.filter(APIUsageLog.create_dt <= end_date)
            
            # 정렬 및 페이징
            query = query.order_by(desc(APIUsageLog.create_dt))
            query = query.limit(limit).offset(offset)
            
            return query.all()
        except Exception as e:
            logger.error(f"사용 이력 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_logs_count(
        self,
        user_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        service_name: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """사용 이력 개수 조회"""
        try:
            query = self.db.query(sql_func.count(APIUsageLog.log_id))
            
            # 필터 조건 추가
            if user_id:
                query = query.filter(APIUsageLog.user_id == user_id)
            if employee_id:
                query = query.filter(APIUsageLog.employee_id == employee_id)
            if service_name:
                query = query.filter(APIUsageLog.service_name == service_name)
            if endpoint:
                query = query.filter(APIUsageLog.endpoint.like(f"%{endpoint}%"))
            if method:
                query = query.filter(APIUsageLog.method == method)
            if start_date:
                query = query.filter(APIUsageLog.create_dt >= start_date)
            if end_date:
                query = query.filter(APIUsageLog.create_dt <= end_date)
            
            return query.scalar() or 0
        except Exception as e:
            logger.error(f"사용 이력 개수 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_service_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[dict]:
        """서비스별 사용 통계"""
        try:
            query = self.db.query(
                APIUsageLog.service_name,
                sql_func.count(APIUsageLog.log_id).label('count'),
                sql_func.avg(APIUsageLog.response_time).label('avg_response_time'),
            )
            
            if start_date:
                query = query.filter(APIUsageLog.create_dt >= start_date)
            if end_date:
                query = query.filter(APIUsageLog.create_dt <= end_date)
            
            query = query.group_by(APIUsageLog.service_name)
            query = query.order_by(desc('count'))
            
            results = query.all()
            return [
                {
                    "service_name": row.service_name or "unknown",
                    "count": row.count,
                    "avg_response_time": round(row.avg_response_time, 2) if row.avg_response_time else None,
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"서비스 통계 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)
    
    def get_user_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[dict]:
        """사용자별 사용 통계 (상위 N명)"""
        try:
            query = self.db.query(
                APIUsageLog.user_id,
                APIUsageLog.employee_id,
                sql_func.count(APIUsageLog.log_id).label('count'),
            )
            
            if start_date:
                query = query.filter(APIUsageLog.create_dt >= start_date)
            if end_date:
                query = query.filter(APIUsageLog.create_dt <= end_date)
            
            query = query.filter(APIUsageLog.user_id.isnot(None))
            query = query.group_by(APIUsageLog.user_id, APIUsageLog.employee_id)
            query = query.order_by(desc('count'))
            query = query.limit(limit)
            
            results = query.all()
            return [
                {
                    "user_id": row.user_id,
                    "employee_id": row.employee_id,
                    "count": row.count,
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"사용자 통계 조회 실패: {str(e)}")
            raise HandledException(ResponseCode.DATABASE_QUERY_ERROR, e=e)

