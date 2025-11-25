# _*_ coding: utf-8 _*_
"""Usage Log API endpoints for operators."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.services.usage_log_service import UsageLogService
from src.core.dependencies import get_db
from src.types.response.auth_response import AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["usage-log"])


def get_usage_log_service(
    db: Session = Depends(get_db)
) -> UsageLogService:
    """사용 이력 서비스 의존성 주입"""
    return UsageLogService(db=db)


@router.get("/usage-logs")
def get_usage_logs(
    user_id: Optional[str] = Query(None, description="사용자 ID"),
    employee_id: Optional[str] = Query(None, description="사번"),
    service_name: Optional[str] = Query(None, description="서비스명 (chat, document, user 등)"),
    endpoint: Optional[str] = Query(None, description="엔드포인트 (부분 일치)"),
    method: Optional[str] = Query(None, description="HTTP 메서드 (GET, POST, PUT, DELETE)"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD 또는 ISO 형식)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD 또는 ISO 형식)"),
    limit: int = Query(100, ge=1, le=1000, description="조회 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    usage_log_service: UsageLogService = Depends(get_usage_log_service),
) -> dict:
    """
    API 사용 이력 조회 (운영자용)
    
    사용자가 어떤 기능을 어떻게 사용했는지 추적한 이력을 조회합니다.
    다양한 필터 조건을 지원합니다.
    """
    logger.info(f"사용 이력 조회 요청: user_id={user_id}, service_name={service_name}")
    
    # 날짜 파싱
    parsed_start_date = None
    parsed_end_date = None
    
    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid start_date format: {start_date}")
    
    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid end_date format: {end_date}")
    
    result = usage_log_service.get_logs(
        user_id=user_id,
        employee_id=employee_id,
        service_name=service_name,
        endpoint=endpoint,
        method=method,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        limit=limit,
        offset=offset,
    )
    
    return result


@router.get("/usage-logs/statistics/service")
def get_service_statistics(
    days: int = Query(7, ge=1, le=365, description="조회 기간 (일)"),
    usage_log_service: UsageLogService = Depends(get_usage_log_service),
) -> dict:
    """
    서비스별 사용 통계 조회 (운영자용)
    
    각 서비스(chat, document, user 등)별 사용 횟수와 평균 응답 시간을 조회합니다.
    """
    logger.info(f"서비스 통계 조회 요청: days={days}")
    
    statistics = usage_log_service.get_service_statistics(days=days)
    
    return {
        "period_days": days,
        "statistics": statistics,
    }


@router.get("/usage-logs/statistics/user")
def get_user_statistics(
    days: int = Query(7, ge=1, le=365, description="조회 기간 (일)"),
    limit: int = Query(10, ge=1, le=100, description="상위 N명"),
    usage_log_service: UsageLogService = Depends(get_usage_log_service),
) -> dict:
    """
    사용자별 사용 통계 조회 (운영자용)
    
    사용자별 API 사용 횟수를 조회합니다. 가장 많이 사용한 사용자 순으로 정렬됩니다.
    """
    logger.info(f"사용자 통계 조회 요청: days={days}, limit={limit}")
    
    statistics = usage_log_service.get_user_statistics(days=days, limit=limit)
    
    return {
        "period_days": days,
        "limit": limit,
        "statistics": statistics,
    }

