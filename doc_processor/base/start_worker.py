#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고성능 Prefect Worker 시작 스크립트
- 성능 최적화 설정들 적용
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def start_fast_worker():
    """고성능 Worker 시작"""
    
    # 현재 Python 인터프리터 사용
    python_path = sys.executable
    
    # 환경변수에서 설정 읽기 (기본값 제공)
    prefect_api_url = os.environ.get('PREFECT_API_URL', 'http://127.0.0.1:4200/api')
    work_pool = os.environ.get('PREFECT_WORK_POOL', 'default')
    work_queue = os.environ.get('PREFECT_WORK_QUEUE', 'default')
    worker_name = os.environ.get('PREFECT_WORKER_NAME', 'fast-worker-optimized')
    worker_limit = os.environ.get('PREFECT_WORKER_LIMIT', '1')
    prefetch_seconds = os.environ.get('PREFECT_PREFETCH_SECONDS', '1')
    
    # 환경변수 설정 (성능 최적화)
    env = os.environ.copy()
    env.update({
        'PREFECT_API_URL': prefect_api_url,
        'PREFECT_TELEMETRY_ENABLED': 'false',  # 텔레메트리 비활성화
        'PREFECT_LOGGING_LEVEL': 'WARNING',    # 로깅 레벨 높임 (성능 향상)
        'PREFECT_TASK_RUN_TAG_CONCURRENCY_SLOT_WAIT_SECONDS': '0.1',  # 대기 시간 단축
        'PREFECT_WORKER_QUERY_SECONDS': '1',   # 쿼리 간격 단축
    })
    # 윈도우 인코딩 문제 해결을 위한 환경변수 설정
    if platform.system() == "Windows":
        env['PYTHONIOENCODING'] = 'utf-8'
    
    # Worker 명령 구성 (환경변수 사용)
    cmd = [
        python_path, "-m", "prefect",
        "worker", "start",
        "--pool", work_pool,
        "--name", worker_name,
        "--limit", worker_limit,
        "--prefetch-seconds", prefetch_seconds,
    ]
    
    # Work queue가 지정된 경우 추가
    if work_queue and work_queue != "default":
        cmd.extend(["--work-queue", work_queue])
    
    print("🚀 고성능 Worker 시작:")
    print(f"   - Pool: {work_pool}")
    print(f"   - Name: {worker_name}")
    print(f"   - Queue: {work_queue}")
    print(f"   - 동시 실행: {worker_limit}개")
    print(f"   - 로깅 레벨: WARNING")
    print(f"   - 텔레메트리: 비활성화")
    print(f"   - 프리페치: {prefetch_seconds}초")
    print(f"   - API URL: {prefect_api_url}")
    print()
    
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\n🛑 Worker 종료됨")

if __name__ == "__main__":
    start_fast_worker()
