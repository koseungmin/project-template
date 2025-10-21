#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prefect Server 시작 스크립트
- 로컬 서버를 시작하여 UI 접근 및 스케줄 관리 가능
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def kill_existing_prefect_processes():
    """기존 Prefect 프로세스 종료"""
    print("🔄 기존 Prefect 프로세스 확인 중...")
    try:
        # Prefect 서버 프로세스 찾기 및 종료
        result = subprocess.run(['pgrep', '-f', 'prefect.*server'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"⚡ 기존 Prefect 서버 프로세스 종료: PID {pid}")
                    os.kill(int(pid), signal.SIGTERM)
                    time.sleep(1)
        
        # Prefect worker 프로세스 찾기 및 종료
        result = subprocess.run(['pgrep', '-f', 'prefect.*worker'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"⚡ 기존 Prefect 워커 프로세스 종료: PID {pid}")
                    os.kill(int(pid), signal.SIGTERM)
                    time.sleep(1)
                    
    except Exception as e:
        print(f"⚠️ 프로세스 정리 중 오류 (무시): {e}")


def start_prefect_server():
    """Prefect 서버 시작"""
    print("🚀 Prefect Server 시작 중...")
    
    # 가상환경의 prefect 경로
    venv_path = Path(__file__).parent.parent / "venv_py312"
    prefect_path = venv_path / "bin" / "prefect"
    
    if not prefect_path.exists():
        print(f"❌ Prefect를 찾을 수 없습니다: {prefect_path}")
        return False
    
    try:
        # 환경변수 설정
        env = os.environ.copy()
        env['PREFECT_TELEMETRY_ENABLED'] = 'false'
        env['PREFECT_API_URL'] = 'http://127.0.0.1:4200/api'
        env['PREFECT_UI_URL'] = 'http://127.0.0.1:4200'
        
        # Prefect 서버 시작
        print("🔧 Prefect Server 구동 중...")
        cmd = [str(prefect_path), "server", "start", "--host", "0.0.0.0", "--port", "4200"]
        
        print(f"실행 명령: {' '.join(cmd)}")
        print("=" * 60)
        print("🌐 Prefect UI: http://127.0.0.1:4200")
        print("🔗 API 엔드포인트: http://127.0.0.1:4200/api")
        print("=" * 60)
        print("📋 다음 단계:")
        print("   1. 🌐 브라우저에서 http://127.0.0.1:4200 접속")
        print("   2. 📊 Flows 메뉴에서 플로우 확인")
        print("   3. ⏰ Deployments에서 스케줄 설정")
        print("   4. ▶️  Quick Run으로 즉시 실행")
        print("=" * 60)
        print("⚠️  종료하려면 Ctrl+C 누르세요")
        print()
        
        # 서버 실행
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print("\n🛑 Prefect Server 종료 중...")
        return True
    except Exception as e:
        print(f"❌ Prefect Server 시작 실패: {e}")
        return False


def main():
    """메인 함수"""
    print("🔧 Prefect Server 관리자")
    print("=" * 60)
    
    # 기존 프로세스 정리
    kill_existing_prefect_processes()
    
    # 서버 시작
    success = start_prefect_server()
    
    if success:
        print("✅ Prefect Server가 정상적으로 종료되었습니다.")
        return 0
    else:
        print("❌ Prefect Server 실행에 문제가 발생했습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())