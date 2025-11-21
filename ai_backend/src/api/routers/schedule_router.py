# _*_ coding: utf-8 _*_
"""Schedule REST API endpoints for Prefect."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
import logging

from src.api.services.schedule_service import ScheduleService
from src.core.dependencies import get_schedule_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["schedule"])


@router.get("/schedules/deployments")
def get_deployments(
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    flow_name: Optional[str] = Query(None, description="Flow 이름 필터"),
    work_pool_name: Optional[str] = Query(None, description="Work Pool 이름 필터"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """Deployment 목록을 조회합니다."""
    try:
        result = schedule_service.get_deployments(
            limit=limit,
            offset=offset,
            flow_name=flow_name,
            work_pool_name=work_pool_name
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get deployments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment 목록 조회 실패: {str(e)}"
        )


@router.get("/schedules/deployments/{deployment_id}")
def get_deployment(
    deployment_id: str,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """특정 Deployment를 조회합니다."""
    try:
        result = schedule_service.get_deployment(deployment_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get deployment {deployment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment 조회 실패: {str(e)}"
        )


@router.get("/schedules/flows")
def get_flows(
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    name: Optional[str] = Query(None, description="Flow 이름 필터"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """Flow 목록을 조회합니다."""
    try:
        result = schedule_service.get_flows(
            limit=limit,
            offset=offset,
            name=name
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flow 목록 조회 실패: {str(e)}"
        )


@router.get("/schedules/flows/{flow_id}")
def get_flow(
    flow_id: str,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """특정 Flow를 조회합니다."""
    try:
        result = schedule_service.get_flow(flow_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flow 조회 실패: {str(e)}"
        )


@router.get("/schedules/flow-runs")
def get_flow_runs(
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    deployment_id: Optional[str] = Query(None, description="Deployment ID 필터"),
    flow_id: Optional[str] = Query(None, description="Flow ID 필터"),
    state_type: Optional[str] = Query(None, description="상태 타입 필터 (PENDING, RUNNING, COMPLETED, FAILED 등)"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """Flow Run 목록을 조회합니다."""
    try:
        result = schedule_service.get_flow_runs(
            limit=limit,
            offset=offset,
            deployment_id=deployment_id,
            flow_id=flow_id,
            state_type=state_type
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get flow runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flow Run 목록 조회 실패: {str(e)}"
        )


@router.get("/schedules/flow-runs/{flow_run_id}")
def get_flow_run(
    flow_run_id: str,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """특정 Flow Run을 조회합니다."""
    try:
        result = schedule_service.get_flow_run(flow_run_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get flow run {flow_run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flow Run 조회 실패: {str(e)}"
        )


@router.get("/schedules/work-pools")
def get_work_pools(
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """Work Pool 목록을 조회합니다."""
    try:
        result = schedule_service.get_work_pools(
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get work pools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Work Pool 목록 조회 실패: {str(e)}"
        )


@router.get("/schedules/work-pools/{work_pool_id}")
def get_work_pool(
    work_pool_id: str,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """특정 Work Pool을 조회합니다."""
    try:
        result = schedule_service.get_work_pool(work_pool_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get work pool {work_pool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Work Pool 조회 실패: {str(e)}"
        )


@router.get("/schedules/work-queues")
def get_work_queues(
    work_pool_id: Optional[str] = Query(None, description="Work Pool ID 필터"),
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """Work Queue 목록을 조회합니다."""
    try:
        result = schedule_service.get_work_queues(
            work_pool_id=work_pool_id,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get work queues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Work Queue 목록 조회 실패: {str(e)}"
        )


@router.get("/schedules/work-queues/{work_queue_id}")
def get_work_queue(
    work_queue_id: str,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """특정 Work Queue를 조회합니다."""
    try:
        result = schedule_service.get_work_queue(work_queue_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get work queue {work_queue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Work Queue 조회 실패: {str(e)}"
        )

