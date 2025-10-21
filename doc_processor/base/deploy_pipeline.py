#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prefect에서 파이프라인을 배포하는 스크립트
- prefect.yaml 파일을 기반으로 배포
- UI에서 스케줄 관리 및 실행 가능
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """명령어 실행"""
    print(f"🔄 {description}...")
    print(f"실행 명령: {' '.join(cmd)}")
    
    try:
        # 환경변수 설정
        env = os.environ.copy()
        env['PREFECT_TELEMETRY_ENABLED'] = 'false'
        env['PREFECT_API_URL'] = 'http://127.0.0.1:4200/api'
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        print(f"✅ {description} 완료")
        if result.stdout:
            print(f"출력: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 실패")
        print(f"에러: {e.stderr}")
        if e.stdout:
            print(f"출력: {e.stdout}")
        return False


def deploy_pipeline():
    """파이프라인 배포"""
    print("🚀 문서 처리 파이프라인을 Prefect에 배포합니다...")
    print("=" * 60)
    
    # 가상환경의 prefect 경로
    venv_path = Path(__file__).parent.parent / "venv_py312"
    prefect_path = venv_path / "bin" / "prefect"
    
    if not prefect_path.exists():
        print(f"❌ Prefect를 찾을 수 없습니다: {prefect_path}")
        return False
    
    # prefect.yaml 파일 확인
    prefect_yaml = Path(__file__).parent.parent / "prefect.yaml"
    if not prefect_yaml.exists():
        print(f"❌ prefect.yaml 파일을 찾을 수 없습니다: {prefect_yaml}")
        print("💡 먼저 prefect.yaml 파일을 생성해주세요.")
        return False
    
    # 배포 실행
    print("📋 파이프라인 배포")
    deploy_cmd = [
        str(prefect_path), "deploy", "--all"
    ]
    
    if not run_command(deploy_cmd, "파이프라인 배포"):
        return False
    
    print("=" * 60)
    print("🎉 파이프라인 배포 완료!")
    print("📋 다음 단계:")
    print("   1. 🌐 브라우저에서 http://127.0.0.1:4200 접속")
    print("   2. 📊 Deployments 메뉴로 이동")
    print("   3. 🔍 배포된 파이프라인 확인")
    print("   4. ⏰ 스케줄 설정 (선택사항)")
    print("   5. ▶️  Quick Run으로 즉시 실행")
    print("=" * 60)
    
    return True


def main():
    """메인 함수"""
    success = deploy_pipeline()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
