# _*_ coding: utf-8 _*_
"""Prefect Schedule Service for querying Prefect API."""
import logging
from typing import Any, Dict, List, Optional

import httpx
from src.config import settings
from src.types.response.exceptions import HandledException
from src.types.response.response_code import ResponseCode

logger = logging.getLogger(__name__)


class ScheduleService:
    """Prefect API를 호출하여 스케줄 정보를 조회하는 서비스"""
    
    def __init__(self):
        # Prefect API URL 설정에서 가져오기
        prefect_api_url = settings.prefect_api_url.rstrip('/')
        
        # Prefect API는 /api 경로를 사용 (v1 없음)
        if "/api" in prefect_api_url:
            # 이미 /api가 포함된 경우 (예: http://0.0.0.0:4200/api)
            self.base_url = prefect_api_url
        else:
            # /api가 없는 경우 (예: http://0.0.0.0:4200)
            self.base_url = f"{prefect_api_url}/api"
        
        logger.info(f"Prefect Schedule Service initialized with API URL: {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Prefect API에 HTTP 요청을 보내는 내부 메서드"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                if json_data:
                    # POST 요청 시 JSON 데이터 전송
                    response = client.request(method, url, json=json_data)
                else:
                    # GET 요청 시 params 사용
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
    
    def get_deployment_by_name(self, deployment_name: str) -> Dict[str, Any]:
        """
        Deployment 이름으로 조회
        
        flow_name과 deployment_name이 같다고 가정하지만, 
        실제로는 다를 수 있으므로 먼저 deployment 목록에서 찾아서 flow_name을 확인합니다.
        """
        try:
            # 먼저 deployment 목록에서 찾기
            deployments_result = self._make_request("POST", "/deployments/paginate", json_data={"limit": 100})
            deployments = deployments_result.get("results", [])
            
            # deployment_name으로 찾기 (정확히 일치하거나 포함)
            deployment = None
            for dep in deployments:
                if dep.get("name") == deployment_name or dep.get("name").replace("-", "_") == deployment_name.replace("-", "_"):
                    deployment = dep
                    break
            
            if not deployment:
                # 찾지 못한 경우, flow_name과 deployment_name이 같다고 가정하고 시도
                return self._make_request("GET", f"/deployments/name/{deployment_name}/{deployment_name}")
            
            # deployment를 찾았으면 flow_id로 flow_name 확인
            flow_id = deployment.get("flow_id")
            if flow_id:
                try:
                    flow = self._make_request("GET", f"/flows/{flow_id}")
                    flow_name = flow.get("name")
                    if flow_name:
                        # flow_name과 deployment_name으로 정확히 조회
                        return self._make_request("GET", f"/deployments/name/{flow_name}/{deployment.get('name')}")
                except Exception:
                    pass
            
            # flow_name을 찾지 못한 경우 deployment 객체 반환
            return deployment
            
        except Exception as e:
            logger.warning(f"Deployment 목록에서 찾기 실패, 직접 시도: {e}")
            # 실패 시 flow_name과 deployment_name이 같다고 가정하고 시도
            return self._make_request("GET", f"/deployments/name/{deployment_name}/{deployment_name}")
    
    def get_flows(
        self,
        limit: int = 100,
        offset: int = 0,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Flow 목록 조회
        
        Returns:
            Flow 목록과 total 개수를 포함한 표준 형식으로 반환
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if name:
            params["name"] = name
        
        result = self._make_request("GET", "/flows", params=params)
        
        # Prefect API 응답 구조에 따라 처리
        # 응답이 리스트인 경우
        if isinstance(result, list):
            flows = result
            total_count = len(flows)
        # 응답이 딕셔너리이고 items나 results 필드가 있는 경우
        elif isinstance(result, dict):
            flows = result.get("items", result.get("results", result.get("data", [])))
            total_count = result.get("total", result.get("count", len(flows)))
        else:
            flows = []
            total_count = 0
        
        return {
            "items": flows,
            "total": total_count,
            "count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    def get_flow(self, flow_id: str) -> Dict[str, Any]:
        """특정 Flow 조회"""
        return self._make_request("GET", f"/flows/{flow_id}")
    
    def get_flow_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        deployment_id: Optional[str] = None,
        flow_id: Optional[str] = None,
        state_type: Optional[str] = None,
        exclude_task_runs: bool = True
    ) -> Dict[str, Any]:
        """
        Flow Run 목록 조회 (paginate 사용)
        
        Args:
            exclude_task_runs: True인 경우 task run 정보를 제외하고 flow run 레벨만 반환
        """
        json_data = {
            "limit": limit,
            "offset": offset
        }
        
        if deployment_id:
            json_data["deployment_id"] = deployment_id
        if flow_id:
            json_data["flow_id"] = flow_id
        if state_type:
            json_data["state_type"] = state_type
        
        result = self._make_request("POST", "/flow_runs/paginate", json_data=json_data)
        # Prefect API의 paginate 응답을 표준 형식으로 변환
        # Prefect API 응답 구조: {"count": 필터조건에맞는전체개수, "results": [현재페이지결과]}
        # count는 limit/offset 적용 전의 필터 조건에 맞는 전체 개수여야 함
        
        # 응답 구조 디버깅 (개발 중에만 활성화)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Paginate response keys: {result.keys()}")
            logger.debug(f"Paginate response count: {result.get('count')}")
            logger.debug(f"Paginate response results length: {len(result.get('results', []))}")
            logger.debug(f"Request params: limit={limit}, offset={offset}, filters={json_data}")
        
        total_count = result.get("count")
        
        # count가 None이거나 잘못된 값인 경우 처리
        if total_count is None:
            logger.warning(f"Paginate response missing 'count' field. Response keys: {result.keys()}")
            # limit=0으로 전체 개수만 조회 시도 (results는 빈 배열이지만 count는 전체 개수 반환)
            try:
                count_json_data = {k: v for k, v in json_data.items() if k != "offset"}
                count_json_data["limit"] = 0  # limit=0으로 설정하여 전체 개수만 가져오기
                count_result = self._make_request("POST", "/flow_runs/paginate", json_data=count_json_data)
                total_count = count_result.get("count", len(result.get("results", [])))
                logger.info(f"Got total count from limit=0 query: {total_count}")
            except Exception as e:
                logger.warning(f"Failed to get total count with limit=0: {e}")
                # fallback: 현재 페이지 결과 개수 사용 (부정확하지만 최소한의 정보 제공)
                total_count = len(result.get("results", []))
        elif total_count == 0 and len(result.get("results", [])) > 0:
            # count가 0인데 results가 있는 경우는 이상함, 로깅
            logger.warning(f"Count is 0 but results exist. This may indicate an API issue.")
        
        flow_runs = result.get("results", [])
        
        # task run 정보 제외하고 flow run 레벨만 반환
        if exclude_task_runs:
            # flow_name과 deployment_name을 가져오기 위해 flow_id와 deployment_id 수집
            flow_ids = set()
            deployment_ids = set()
            for flow_run in flow_runs:
                flow_id = flow_run.get("flow_id")
                deployment_id = flow_run.get("deployment_id")
                if flow_id:
                    flow_ids.add(flow_id)
                if deployment_id:
                    deployment_ids.add(deployment_id)
            
            # flow_id와 deployment_id로 이름 정보 조회 (배치 처리)
            flow_name_map = {}
            deployment_name_map = {}
            
            # Flow 이름 조회
            for flow_id in flow_ids:
                try:
                    flow_info = self.get_flow(flow_id)
                    flow_name_map[flow_id] = flow_info.get("name")
                except Exception as e:
                    logger.warning(f"Failed to get flow name for {flow_id}: {e}")
                    flow_name_map[flow_id] = None
            
            # Deployment 이름 조회
            for deployment_id in deployment_ids:
                try:
                    deployment_info = self.get_deployment(deployment_id)
                    deployment_name_map[deployment_id] = deployment_info.get("name")
                except Exception as e:
                    logger.warning(f"Failed to get deployment name for {deployment_id}: {e}")
                    deployment_name_map[deployment_id] = None
            
            flow_run_summaries = []
            for flow_run in flow_runs:
                flow_id = flow_run.get("flow_id")
                deployment_id = flow_run.get("deployment_id")
                
                # Flow Run 레벨 정보만 추출 (task run 정보 완전 제외)
                flow_run_summary = {
                    "id": flow_run.get("id"),
                    "name": flow_run.get("name"),
                    "flow_id": flow_id,
                    "flow_name": flow_name_map.get(flow_id) if flow_id else None,
                    "deployment_id": deployment_id,
                    "deployment_name": deployment_name_map.get(deployment_id) if deployment_id else None,
                    "state_type": flow_run.get("state_type"),
                    "state_name": flow_run.get("state_name"),
                    "start_time": flow_run.get("start_time"),
                    "end_time": flow_run.get("end_time"),
                    "expected_start_time": flow_run.get("expected_start_time"),
                    "created": flow_run.get("created"),
                    "updated": flow_run.get("updated"),
                    "run_count": flow_run.get("run_count", 0),
                    # task_runs, task_run_id 등 task run 관련 필드는 완전히 제외
                }
                
                # state 객체에서 task run 정보 제거
                state = flow_run.get("state")
                if state and isinstance(state, dict):
                    state_summary = {
                        "id": state.get("id"),
                        "type": state.get("type"),
                        "name": state.get("name"),
                        "message": state.get("message"),
                        "timestamp": state.get("timestamp"),
                        # task_runs, task_run_id 등 task run 관련 필드는 제외
                    }
                    flow_run_summary["state"] = state_summary
                else:
                    flow_run_summary["state"] = state
                
                flow_run_summaries.append(flow_run_summary)
            
            return {
                "items": flow_run_summaries,  # task run 정보가 제외된 flow run만 반환
                "total": total_count,
                "count": total_count,
                "limit": limit,
                "offset": offset
            }
        else:
            # task run 정보 포함 (기존 동작)
            return {
                "items": flow_runs,
                "total": total_count,
                "count": total_count,
                "limit": limit,
                "offset": offset
            }
    
    def get_flow_runs_by_flow_id(
        self,
        flow_id: str,
        limit: int = 100,
        offset: int = 0,
        state_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        특정 Flow의 Flow Run 목록 조회 (Flow 단위, Task Run 정보 제외)
        
        화면에서 flow를 클릭해서 list로 들어갈 때 사용하는 메서드입니다.
        Flow Run 레벨 정보만 반환하며, Task Run 정보는 제외합니다.
        
        Args:
            flow_id: Flow ID
            limit: 조회할 개수
            offset: 건너뛸 개수
            state_type: 상태 타입 필터
        
        Returns:
            Flow Run 목록 (Task Run 정보 제외)
        """
        # flow_id로 flow_runs 조회
        # get_flow_runs가 이미 task run 정보를 제외하고 flow run 레벨만 반환함
        flow_runs_result = self.get_flow_runs(
            limit=limit,
            offset=offset,
            flow_id=flow_id,
            state_type=state_type,
            exclude_task_runs=True  # task run 정보 제외하고 flow run 레벨만 반환
        )
        
        return {
            "flow_id": flow_id,
            "total": flow_runs_result.get("total", 0),
            "count": flow_runs_result.get("count", flow_runs_result.get("total", 0)),
            "limit": limit,
            "offset": offset,
            "items": flow_runs_result.get("items", [])  # task run 정보가 제외된 Flow Run 목록만 반환
        }
    
    def get_flow_run(self, flow_run_id: str) -> Dict[str, Any]:
        """특정 Flow Run 조회"""
        return self._make_request("GET", f"/flow_runs/{flow_run_id}")
    
    def get_flow_run_parameters(self, flow_run_id: str) -> Dict[str, Any]:
        """
        Flow Run의 파라미터 조회
        
        Flow Run 조회 시 parameters 필드에서 파라미터를 가져옵니다.
        parameters는 flow 실행 시 전달된 파라미터입니다.
        
        참고: input은 flow run 실행 중 동적으로 생성되는 입력 데이터로,
        parameters와는 다른 개념입니다.
        
        Args:
            flow_run_id: Flow Run ID
        
        Returns:
            Flow Run의 파라미터 정보
        """
        try:
            # Flow Run 정보 가져오기
            flow_run = self.get_flow_run(flow_run_id)
            
            # parameters 필드 추출 (없으면 빈 딕셔너리)
            parameters = flow_run.get("parameters")
            if parameters is None:
                parameters = {}
            
            return {
                "flow_run_id": flow_run_id,
                "parameters": parameters,
                "flow_run_name": flow_run.get("name"),
                "deployment_id": flow_run.get("deployment_id"),
                "flow_id": flow_run.get("flow_id")
            }
                
        except Exception as e:
            logger.error(f"Failed to get flow run parameters for {flow_run_id}: {e}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"Flow Run 파라미터 조회 실패: {str(e)}"
            )
    
    def get_flow_run_logs(self, flow_run_id: str) -> Dict[str, Any]:
        """Flow Run 로그 조회"""
        # Prefect API는 /api/logs/filter를 사용하여 flow_run_id로 필터링
        json_data = {
            "flow_runs": {"id": {"any_": [flow_run_id]}},
            "limit": 1000
        }
        return self._make_request("POST", "/logs/filter", json_data=json_data)
    
    def set_flow_run_state(
        self,
        flow_run_id: str,
        state_type: str,
        name: Optional[str] = None,
        message: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Flow Run 상태 변경
        
        Prefect API의 set_state 엔드포인트를 사용하여 flow run의 상태를 변경합니다.
        orchestration rules가 적용되어 상태 전이가 거부될 수 있습니다.
        
        Args:
            flow_run_id: Flow Run ID
            state_type: 상태 타입 (SCHEDULED, PENDING, RUNNING, COMPLETED, FAILED, 
                       CANCELLED, CRASHED, PAUSED, CANCELLING)
            name: 상태 이름 (선택사항)
            message: 상태 메시지 (선택사항)
            force: True인 경우 orchestration rules를 무시하고 강제로 상태 변경
        
        Returns:
            상태 변경 결과 (state, status, details 포함)
            
        참고:
            - status는 ACCEPT, REJECT, ABORT, WAIT 중 하나
            - force=False인 경우 Prefect의 상태 전이 규칙이 적용됨
        """
        try:
            json_data = {
                "state": {
                    "type": state_type
                },
                "force": force
            }
            
            if name:
                json_data["state"]["name"] = name
            if message:
                json_data["state"]["message"] = message
            
            result = self._make_request("POST", f"/flow_runs/{flow_run_id}/set_state", json_data=json_data)
            logger.info(f"Flow run {flow_run_id} state changed to {state_type}, status: {result.get('status')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to set flow run state for {flow_run_id}: {e}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"Flow Run 상태 변경 실패: {str(e)}"
            )
    
    def cancel_flow_run(self, flow_run_id: str, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Flow Run 취소
        
        실행 중이거나 대기 중인 flow run을 취소합니다.
        
        Args:
            flow_run_id: Flow Run ID
            message: 취소 메시지 (선택사항)
        
        Returns:
            상태 변경 결과
        """
        cancel_message = message or "Cancelled by user"
        return self.set_flow_run_state(
            flow_run_id=flow_run_id,
            state_type="CANCELLED",
            name="Cancelled",
            message=cancel_message,
            force=False
        )
    
    def retry_flow_run(self, flow_run_id: str, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Flow Run 재시도
        
        실패하거나 취소된 flow run을 재시도하기 위해 PENDING 상태로 변경합니다.
        
        Args:
            flow_run_id: Flow Run ID
            message: 재시도 메시지 (선택사항)
        
        Returns:
            상태 변경 결과
            
        참고:
            - 실패한 flow run을 재시도하려면 PENDING 또는 SCHEDULED 상태로 변경
            - orchestration rules에 따라 상태 전이가 거부될 수 있음
        """
        retry_message = message or "Retrying failed flow run"
        return self.set_flow_run_state(
            flow_run_id=flow_run_id,
            state_type="PENDING",
            name="Pending",
            message=retry_message,
            force=False
        )
    
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
    
    def get_schedules(
        self,
        limit: int = 100,
        offset: int = 0,
        deployment_id: Optional[str] = None,
        flow_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        스케줄 목록 조회
        
        Prefect API에는 스케줄을 직접 조회하는 엔드포인트가 없으므로,
        Deployment 목록을 조회한 후 각 Deployment의 스케줄 정보를 추출하여 반환합니다.
        """
        try:
            # 1. Deployment 목록 조회
            deployments_result = self.get_deployments(
                limit=limit,
                offset=offset,
                flow_name=flow_name
            )
            
            deployments = deployments_result.get("items", [])
            
            # 2. 각 Deployment에서 스케줄 정보 추출
            schedules = []
            for deployment in deployments:
                dep_id = deployment.get("id")
                
                # deployment_id 필터가 있는 경우 필터링
                if deployment_id and dep_id != deployment_id:
                    continue
                
                # Deployment에 스케줄 정보가 포함되어 있는지 확인
                schedule = deployment.get("schedule")
                
                if schedule:
                    # 스케줄 정보가 있으면 추가
                    schedule_item = {
                        "deployment_id": dep_id,
                        "deployment_name": deployment.get("name"),
                        "flow_id": deployment.get("flow_id"),
                        "flow_name": deployment.get("flow_name"),
                        "schedule": schedule,
                        "is_schedule_active": deployment.get("is_schedule_active", True),
                        "created": deployment.get("created"),
                        "updated": deployment.get("updated")
                    }
                    schedules.append(schedule_item)
                elif not deployment_id:
                    # 스케줄이 없어도 deployment_id 필터가 없으면 포함 (스케줄 없는 것도 정보)
                    schedule_item = {
                        "deployment_id": dep_id,
                        "deployment_name": deployment.get("name"),
                        "flow_id": deployment.get("flow_id"),
                        "flow_name": deployment.get("flow_name"),
                        "schedule": None,
                        "is_schedule_active": False,
                        "created": deployment.get("created"),
                        "updated": deployment.get("updated")
                    }
                    schedules.append(schedule_item)
            
            # 3. 결과 반환
            return {
                "items": schedules,
                "total": len(schedules),
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get schedules: {e}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"스케줄 목록 조회 실패: {str(e)}"
            )
    
    def get_schedule_list(self) -> Dict[str, Any]:
        """
        환경변수에 설정된 deployment_name 리스트를 기반으로 스케줄 리스트 조회
        
        각 deployment_name으로 deployment를 조회하고 (flow_name과 deployment_name이 같음),
        모든 결과를 합쳐서 반환합니다.
        """
        try:
            deployment_names = settings.get_prefect_deployment_names()
            
            if not deployment_names:
                logger.warning("PREFECT_DEPLOYMENT_NAMES 환경변수가 설정되지 않았습니다.")
                return {
                    "items": [],
                    "total": 0
                }
            
            schedules = []
            errors = []
            
            # 각 deployment_name으로 조회 (flow_name과 deployment_name이 같음)
            for deployment_name in deployment_names:
                try:
                    # GET /deployments/name/{deployment_name}/{deployment_name} 호출
                    deployment = self.get_deployment_by_name(deployment_name)
                    
                    # deployment_id 추출
                    deployment_id = deployment.get("id")
                    if not deployment_id:
                        logger.warning(f"Deployment '{deployment_name}'에서 id를 찾을 수 없습니다.")
                        continue
                    
                    # 스케줄 정보 구성
                    schedule_item = {
                        "deployment_id": deployment_id,
                        "deployment_name": deployment.get("name"),
                        "flow_id": deployment.get("flow_id"),
                        "flow_name": deployment.get("flow_name"),
                        "schedule": deployment.get("schedule"),
                        "is_schedule_active": deployment.get("is_schedule_active", True),
                        "created": deployment.get("created"),
                        "updated": deployment.get("updated")
                    }
                    schedules.append(schedule_item)
                    
                except Exception as e:
                    error_msg = f"Deployment '{deployment_name}' 조회 실패: {str(e)}"
                    logger.error(error_msg)
                    errors.append({
                        "deployment_name": deployment_name,
                        "error": str(e)
                    })
            
            return {
                "items": schedules,
                "total": len(schedules),
                "errors": errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get schedule list: {e}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"스케줄 리스트 조회 실패: {str(e)}"
            )
    
    def get_schedule_history(self, deployment_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        특정 스케줄의 실행 이력 조회 (Deployment 스케줄 단위)
        
        화면에서 deployment로 스케줄을 걸었을 때, 그 스케줄로 실행된 flow run 이력들을 조회합니다.
        
        Args:
            deployment_name: Deployment 이름
            limit: 조회할 개수
            offset: 건너뛸 개수
        
        Returns:
            해당 deployment의 스케줄로 실행된 Flow Run 목록 (Task Run 정보 제외)
        """
        try:
            # 1. deployment_name으로 deployment 조회하여 deployment_id 얻기
            deployment = self.get_deployment_by_name(deployment_name)
            deployment_id = deployment.get("id")
            flow_id = deployment.get("flow_id")
            
            if not deployment_id:
                raise HandledException(
                    ResponseCode.NOT_FOUND,
                    msg=f"Deployment '{deployment_name}'를 찾을 수 없습니다."
                )
            
            # 2. deployment_id로 flow_runs 조회 (해당 deployment의 스케줄로 실행된 flow run만 조회)
            # get_flow_runs가 이미 task run 정보를 제외하고 flow run 레벨만 반환함
            flow_runs_result = self.get_flow_runs(
                limit=limit,
                offset=offset,
                deployment_id=deployment_id,  # deployment_id로 필터링하여 해당 스케줄의 실행 이력만 조회
                exclude_task_runs=True  # task run 정보 제외하고 flow run 레벨만 반환
            )
            
            return {
                "deployment_id": deployment_id,
                "deployment_name": deployment_name,
                "flow_id": flow_id,
                "total": flow_runs_result.get("total", 0),
                "count": flow_runs_result.get("count", flow_runs_result.get("total", 0)),
                "limit": limit,
                "offset": offset,
                "items": flow_runs_result.get("items", [])  # task run 정보가 제외된 Flow Run 목록만 반환
            }
            
        except HandledException:
            raise
        except Exception as e:
            logger.error(f"Failed to get schedule history for {deployment_name}: {e}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"스케줄 실행 이력 조회 실패: {str(e)}"
            )
    
    def create_flow_run(
        self,
        deployment_id: str,
        parameters: Optional[Dict] = None,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deployment에서 새 Flow Run 생성 (플로우 실행)
        
        Args:
            deployment_id: Deployment ID
            parameters: Flow 실행에 필요한 파라미터 (선택사항)
            name: Flow Run 이름 (선택사항)
            tags: 태그 리스트 (선택사항)
        
        Returns:
            생성된 Flow Run 정보
        """
        try:
            json_data = {}
            
            if parameters:
                json_data["parameters"] = parameters
            if name:
                json_data["name"] = name
            if tags:
                json_data["tags"] = tags
            
            result = self._make_request("POST", f"/deployments/{deployment_id}/create_flow_run", json_data=json_data)
            logger.info(f"Flow run created successfully: {result.get('id')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create flow run for deployment {deployment_id}: {e}")
            raise HandledException(
                ResponseCode.INTERNAL_SERVER_ERROR,
                msg=f"Flow Run 생성 실패: {str(e)}"
            )
