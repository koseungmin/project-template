# _*_ coding: utf-8 _*_
"""Prefect Schedule Service for querying Prefect API."""
import logging
import os
from typing import Dict, List, Optional, Any
import httpx

from src.types.response.exceptions import HandledException
from src.types.response.response_code import ResponseCode

logger = logging.getLogger(__name__)


class ScheduleService:
    """Prefect API를 호출하여 스케줄 정보를 조회하는 서비스"""
    
    def __init__(self):
        # Prefect API URL 환경변수에서 가져오기
        # 기본값: http://localhost:4200/scheduler/api (doc-processor 컨테이너)
        prefect_api_url = os.getenv(
            "PREFECT_API_URL", 
            "http://localhost:4200/scheduler/api"
        ).rstrip('/')
        
        # Prefect API 버전 (Prefect 3.0)
        # Prefect 3.0에서는 /api/v1 경로를 사용하지만, 
        # scheduler/api가 이미 prefix로 붙어있으므로 v1만 추가
        if "/api" in prefect_api_url:
            # 이미 /api가 포함된 경우 (예: http://localhost:4200/scheduler/api)
            self.base_url = f"{prefect_api_url}/v1"
        else:
            # /api가 없는 경우 (예: http://localhost:4200)
            self.base_url = f"{prefect_api_url}/api/v1"
        
        logger.info(f"Prefect Schedule Service initialized with API URL: {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Prefect API에 HTTP 요청을 보내는 내부 메서드"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(method, url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Prefect API request failed: {e.response.status_code} - {e.response.text}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"Prefect API 요청 실패: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            logger.error(f"Prefect API connection error: {e}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"Prefect API 연결 실패: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in Prefect API request: {e}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"Prefect API 요청 중 오류 발생: {str(e)}"
            )
    
    def get_deployments(
        self, 
        limit: int = 100, 
        offset: int = 0,
        flow_name: Optional[str] = None,
        work_pool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deployment 목록 조회"""
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if flow_name:
            params["flow_name"] = flow_name
        if work_pool_name:
            params["work_pool_name"] = work_pool_name
        
        return self._make_request("GET", "/deployments", params=params)
    
    def get_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """특정 Deployment 조회"""
        return self._make_request("GET", f"/deployments/{deployment_id}")
    
    def get_flows(
        self,
        limit: int = 100,
        offset: int = 0,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Flow 목록 조회"""
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if name:
            params["name"] = name
        
        return self._make_request("GET", "/flows", params=params)
    
    def get_flow(self, flow_id: str) -> Dict[str, Any]:
        """특정 Flow 조회"""
        return self._make_request("GET", f"/flows/{flow_id}")
    
    def get_flow_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        deployment_id: Optional[str] = None,
        flow_id: Optional[str] = None,
        state_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Flow Run 목록 조회"""
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if deployment_id:
            params["deployment_id"] = deployment_id
        if flow_id:
            params["flow_id"] = flow_id
        if state_type:
            params["state_type"] = state_type
        
        return self._make_request("GET", "/flow_runs", params=params)
    
    def get_flow_run(self, flow_run_id: str) -> Dict[str, Any]:
        """특정 Flow Run 조회"""
        return self._make_request("GET", f"/flow_runs/{flow_run_id}")
    
    def get_work_pools(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Work Pool 목록 조회"""
        params = {
            "limit": limit,
            "offset": offset
        }
        
        return self._make_request("GET", "/work_pools", params=params)
    
    def get_work_pool(self, work_pool_id: str) -> Dict[str, Any]:
        """특정 Work Pool 조회"""
        return self._make_request("GET", f"/work_pools/{work_pool_id}")
    
    def get_work_queues(
        self,
        work_pool_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Work Queue 목록 조회"""
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if work_pool_id:
            params["work_pool_id"] = work_pool_id
        
        return self._make_request("GET", "/work_queues", params=params)
    
    def get_work_queue(self, work_queue_id: str) -> Dict[str, Any]:
        """특정 Work Queue 조회"""
        return self._make_request("GET", f"/work_queues/{work_queue_id}")

