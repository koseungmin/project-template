#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고성능 Prefect Worker 시작 스크립트
- 성능 최적화 설정들 적용
"""

import os
import subprocess
import sys
from pathlib import Path


def start_fast_worker():
    """고성능 Worker 시작"""
    
    # 가상환경의 prefect 경로
    venv_path = Path(__file__).parent.parent / "venv_py312"
    prefect_path = venv_path / "bin" / "prefect"
    
    # 환경변수 설정 (성능 최적화)
    env = os.environ.copy()
    env.update({
        'PREFECT_API_URL': 'http://127.0.0.1:4200/api',
        'PREFECT_TELEMETRY_ENABLED': 'false',  # 텔레메트리 비활성화
        'PREFECT_LOGGING_LEVEL': 'WARNING',    # 로깅 레벨 높임 (성능 향상)
        'PREFECT_TASK_RUN_TAG_CONCURRENCY_SLOT_WAIT_SECONDS': '0.1',  # 대기 시간 단축
        'PREFECT_WORKER_QUERY_SECONDS': '1',   # 쿼리 간격 단축
    })
    
    # 고성능 Worker 명령
    cmd = [
        str(prefect_path),
        "worker", "start",
        "--pool", "default",
        "--name", "fast-worker-optimized", 
        "--limit", "1",                  # 동시 실행 1개
        "--prefetch-seconds", "1",       # 미리 가져오기 최소화
    ]
    
    print("🚀 고성능 Worker 시작:")
    print(f"   - 동시 실행: 1개")
    print(f"   - 로깅 레벨: WARNING")
    print(f"   - 텔레메트리: 비활성화")
    print(f"   - 프리페치: 1초")
    print()
    
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\n🛑 Worker 종료됨")

if __name__ == "__main__":
    start_fast_worker()
