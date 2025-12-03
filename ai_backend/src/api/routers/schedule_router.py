# _*_ coding: utf-8 _*_
"""Schedule REST API endpoints for Prefect."""
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

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


@router.get("/schedules/deployments/name/{deployment_name}")
def get_deployment_by_name(
    deployment_name: str,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """Deployment 이름으로 조회합니다 (flow_name과 deployment_name이 같음)."""
    try:
        result = schedule_service.get_deployment_by_name(deployment_name)
        return result
    except Exception as e:
        logger.error(f"Failed to get deployment by name {deployment_name}: {e}")
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


@router.get("/schedules/flows/{flow_id}/runs")
def get_flow_runs_by_flow_id(
    flow_id: str,
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    state_type: Optional[str] = Query(None, description="상태 타입 필터 (PENDING, RUNNING, COMPLETED, FAILED 등)"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    특정 Flow의 Flow Run 목록을 조회합니다.
    
    화면에서 flow를 클릭해서 list로 들어갈 때 사용하는 엔드포인트입니다.
    Flow Run 레벨 정보만 반환하며, Task Run 정보는 제외합니다.
    """
    try:
        result = schedule_service.get_flow_runs_by_flow_id(
            flow_id=flow_id,
            limit=limit,
            offset=offset,
            state_type=state_type
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get flow runs for flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flow Run 목록 조회 실패: {str(e)}"
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


@router.get("/schedules")
def get_schedules(
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    deployment_id: Optional[str] = Query(None, description="Deployment ID 필터"),
    flow_name: Optional[str] = Query(None, description="Flow 이름 필터"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    스케줄 목록을 조회합니다.
    
    Prefect API에는 스케줄을 직접 조회하는 엔드포인트가 없으므로,
    Deployment 목록을 조회한 후 각 Deployment의 스케줄 정보를 추출하여 반환합니다.
    """
    try:
        result = schedule_service.get_schedules(
            limit=limit,
            offset=offset,
            deployment_id=deployment_id,
            flow_name=flow_name
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스케줄 목록 조회 실패: {str(e)}"
        )


@router.get("/schedules/list")
def get_schedule_list(
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    환경변수에 설정된 deployment_name 리스트를 기반으로 스케줄 리스트를 조회합니다.
    
    PREFECT_DEPLOYMENT_NAMES 환경변수에 설정된 각 deployment_name으로 
    deployment를 조회하고, 모든 결과를 합쳐서 반환합니다.
    """
    try:
        result = schedule_service.get_schedule_list()
        return result
    except Exception as e:
        logger.error(f"Failed to get schedule list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스케줄 리스트 조회 실패: {str(e)}"
        )


@router.get("/schedules/{deployment_name}/history")
def get_schedule_history(
    deployment_name: str,
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    특정 스케줄의 실행 이력을 조회합니다.
    
    deployment_name으로 deployment를 조회하여 deployment_id를 얻고 (flow_name과 deployment_name이 같음),
    해당 deployment_id로 flow_runs를 조회합니다.
    """
    try:
        result = schedule_service.get_schedule_history(
            deployment_name=deployment_name,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get schedule history for {deployment_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스케줄 실행 이력 조회 실패: {str(e)}"
        )


@router.get("/schedules/flow-runs/{flow_run_id}/logs")
def get_flow_run_logs(
    flow_run_id: str,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    Flow Run의 로그를 조회합니다.
    """
    try:
        result = schedule_service.get_flow_run_logs(flow_run_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get flow run logs for {flow_run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flow Run 로그 조회 실패: {str(e)}"
        )


@router.get("/schedules/flow-runs/{flow_run_id}/parameters")
def get_flow_run_parameters(
    flow_run_id: str,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    Flow Run의 파라미터를 조회합니다.
    
    Flow Run 조회 시 parameters 필드에서 파라미터를 가져옵니다.
    parameters는 flow 실행 시 전달된 파라미터입니다.
    
    참고: input은 flow run 실행 중 동적으로 생성되는 입력 데이터로,
    parameters와는 다른 개념입니다.
    """
    try:
        result = schedule_service.get_flow_run_parameters(flow_run_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get flow run parameters for {flow_run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flow Run 파라미터 조회 실패: {str(e)}"
        )


@router.post("/schedules/deployments/{deployment_id}/create-flow-run")
def create_flow_run(
    deployment_id: str,
    parameters: Optional[Dict] = Body(None, description="Flow 실행에 필요한 파라미터"),
    name: Optional[str] = Body(None, description="Flow Run 이름"),
    tags: Optional[List[str]] = Body(None, description="태그 리스트"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    Deployment에서 새 Flow Run을 생성합니다 (플로우 실행).

    특정 Deployment를 실행하여 새로운 Flow Run을 생성합니다.
    """

    result = schedule_service.create_flow_run(
        deployment_id=deployment_id,
        parameters=parameters,
        name=name,
        tags=tags
    )
    return result
