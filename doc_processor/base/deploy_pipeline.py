#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prefect에서 파이프라인을 배포하는 스크립트
- prefect.yaml 파일을 기반으로 배포
- UI에서 스케줄 관리 및 실행 가능
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

import yaml

# 윈도우 인코딩 문제 해결: Python 기본 인코딩을 UTF-8로 설정
if platform.system() == "Windows":
    # Python 3.7+ UTF-8 모드 활성화
    os.environ['PYTHONUTF8'] = '1'
    # 표준 입출력 인코딩 설정
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    if sys.stderr.encoding != 'utf-8':
        try:
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass


def run_command(cmd, description, cwd=None):
    """명령어 실행"""
    print(f"🔄 {description}...")
    print(f"실행 명령: {' '.join(cmd)}")
    
    try:
        # 환경변수 설정
        env = os.environ.copy()
        env['PREFECT_TELEMETRY_ENABLED'] = 'false'
        # PREFECT_API_URL이 환경변수에 있으면 사용, 없으면 기본값
        if 'PREFECT_API_URL' not in env:
            env['PREFECT_API_URL'] = 'http://127.0.0.1:4200/api'
        
        # 윈도우 인코딩 문제 해결을 위한 환경변수 설정 (더 강력한 설정)
        if platform.system() == "Windows":
            # Python 3.7+ UTF-8 모드 활성화
            env['PYTHONUTF8'] = '1'
            # 입출력 인코딩 설정
            env['PYTHONIOENCODING'] = 'utf-8'
            # locale 설정
            env['LC_ALL'] = 'C.UTF-8'
            env['LANG'] = 'C.UTF-8'
            # Windows 코드페이지를 UTF-8로 설정
            try:
                import subprocess as sp

                # 코드페이지를 UTF-8로 변경 (chcp 65001)
                sp.run(['chcp', '65001'], shell=True, capture_output=True, check=False)
            except:
                pass
        
        # subprocess 실행 시 UTF-8 인코딩 명시 (윈도우 cp949 문제 해결)
        # cwd가 지정되지 않으면 prefect.yaml이 있는 디렉토리로 이동
        if cwd is None:
            if 'PREFECT_YAML_PATH' in os.environ:
                yaml_path = Path(os.environ['PREFECT_YAML_PATH'])
                if yaml_path.exists():
                    cwd = str(yaml_path.parent)
        
        result = subprocess.run(
            cmd, 
            cwd=cwd,  # 지정된 작업 디렉토리 또는 prefect.yaml이 있는 디렉토리
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='replace',  # 디코딩 에러 시 대체 문자 사용
            check=True, 
            env=env,
            shell=False  # shell=False로 명시 (윈도우에서 더 안전)
        )
        print(f"✅ {description} 완료")
        if result.stdout:
            print(f"출력: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 실패")
        print(f"반환 코드: {e.returncode}")
        # stderr도 UTF-8로 디코딩 시도
        try:
            if isinstance(e.stderr, bytes):
                error_msg = e.stderr.decode('utf-8', errors='replace')
            else:
                error_msg = e.stderr
            print(f"에러 출력: {error_msg}")
        except Exception as decode_err:
            print(f"에러 디코딩 실패: {decode_err}")
            print(f"원본 에러 (bytes): {e.stderr}")
        if e.stdout:
            try:
                if isinstance(e.stdout, bytes):
                    output_msg = e.stdout.decode('utf-8', errors='replace')
                else:
                    output_msg = e.stdout
                print(f"표준 출력: {output_msg}")
            except Exception as decode_err:
                print(f"출력 디코딩 실패: {decode_err}")
                print(f"원본 출력 (bytes): {e.stdout}")
        return False
    except UnicodeDecodeError as ue:
        print(f"❌ 인코딩 에러 발생: {ue}")
        print(f"에러 위치: {ue.start}-{ue.end}")
        print(f"에러 객체: {ue.object}")
        return False


def deploy_pipeline():
    """파이프라인 배포"""
    print("🚀 문서 처리 파이프라인을 Prefect에 배포합니다...")
    print("=" * 60)
    
    # 현재 Python 인터프리터 사용 (launch.json에서 설정된 가상환경 Python)
    python_path = sys.executable
    
    # prefect.yaml 파일 경로 확인 (환경변수 또는 기본값)
    # Docker: base/prefect.yaml 사용 (절대 경로 /app/flow/...)
    # 로컬: doc_processor/prefect.yaml 사용 (상대 경로 flow/...)
    if 'PREFECT_YAML_PATH' in os.environ:
        prefect_yaml_path = os.environ['PREFECT_YAML_PATH']
    else:
        # 환경 자동 감지
        if os.path.exists("/app"):
            # Docker 환경: base/prefect.yaml 사용
            prefect_yaml_path = str(Path(__file__).parent / "prefect.yaml")
        else:
            # 로컬 환경: doc_processor/prefect.yaml 사용
            local_yaml = Path(__file__).parent.parent / "prefect.yaml"
            if local_yaml.exists():
                prefect_yaml_path = str(local_yaml)
            else:
                # fallback: base/prefect.yaml 사용
                prefect_yaml_path = str(Path(__file__).parent / "prefect.yaml")
    
    prefect_yaml = Path(prefect_yaml_path)
    
    if not prefect_yaml.exists():
        print(f"❌ prefect.yaml 파일을 찾을 수 없습니다: {prefect_yaml}")
        print("💡 환경변수 PREFECT_YAML_PATH로 파일 경로를 지정하거나,")
        print(f"   기본 경로에 prefect.yaml 파일을 생성해주세요.")
        return False
    
    print(f"📄 사용할 prefect.yaml: {prefect_yaml}")
    
    # 배포 실행 (Python 모듈로 실행하는 방식 사용 - 플랫폼 독립적)
    # Docker 환경인지 로컬 환경인지 자동 감지하여 cwd 설정
    # Docker: /app 디렉토리에서 실행
    # 로컬: doc_processor 디렉토리에서 실행 (prefect.yaml의 부모의 부모)
    if os.path.exists("/app"):
        # Docker 환경
        deploy_cwd = "/app"
        print("🐳 Docker 환경 감지: /app 디렉토리에서 실행")
    else:
        # 로컬 환경: prefect.yaml의 부모의 부모 디렉토리 (doc_processor)
        # base/prefect.yaml -> base -> doc_processor
        deploy_cwd = str(prefect_yaml.parent.parent)
        print(f"💻 로컬 환경 감지: {deploy_cwd} 디렉토리에서 실행")
    
    print("📋 파이프라인 배포")
    yaml_dir = prefect_yaml.parent
    
    # Prefect 3.0에서 --all 옵션 사용 (모든 deployment를 한 번에 배포)
    # 환경변수로 개별 배포 모드 선택 가능
    use_individual_deploy = os.environ.get('PREFECT_DEPLOY_INDIVIDUAL', '0') == '1'
    
    if use_individual_deploy:
        # 개별 배포 모드 (에러 발생 시에도 계속 진행)
        print("📦 개별 배포 모드로 실행합니다...")
        try:
            with open(prefect_yaml, 'r', encoding='utf-8') as f:
                yaml_content = yaml.safe_load(f)
            
            deployments = yaml_content.get('deployments', [])
            if not deployments:
                print("⚠️  prefect.yaml에 deployment가 없습니다.")
                return False
            
            print(f"📦 총 {len(deployments)}개의 deployment를 개별 배포합니다.")
            
            success_count = 0
            for idx, deployment in enumerate(deployments, 1):
                deployment_name = deployment.get('name', f'deployment-{idx}')
                print(f"\n{'='*60}")
                print(f"📦 [{idx}/{len(deployments)}] 배포 중: {deployment_name}")
                print(f"{'='*60}")
                
                deploy_cmd = [
                    python_path, "-m", "prefect", "deploy",
                    "--prefect-file", str(prefect_yaml),
                    "--name", deployment_name
                ]
                
                if run_command(deploy_cmd, f"Deployment '{deployment_name}' 배포", cwd=deploy_cwd):
                    success_count += 1
                    print(f"✅ {deployment_name} 배포 성공")
                else:
                    print(f"⚠️  {deployment_name} 배포 실패 (계속 진행)")
            
            print(f"\n{'='*60}")
            print(f"📊 배포 결과: {success_count}/{len(deployments)} 성공")
            print(f"{'='*60}")
            
            if success_count == 0:
                print("❌ 모든 deployment 배포 실패")
                return False
            
        except Exception as e:
            print(f"❌ prefect.yaml 파일 읽기 실패: {e}")
            return False
    else:
        # --all 옵션 사용 (기본 모드)
        # Prefect의 --all 옵션은 하나라도 실패하면 non-zero exit code를 반환하므로
        # check=False로 설정하고 stdout/stderr를 확인하여 실제 성공 여부 판단
        print("📦 --all 옵션으로 모든 deployment를 배포합니다...")
        deploy_cmd = [
            python_path, "-m", "prefect", "deploy",
            "--prefect-file", str(prefect_yaml),
            "--all"
        ]
        
        # check=False로 설정하여 에러가 발생해도 계속 진행
        try:
            env = os.environ.copy()
            env['PREFECT_TELEMETRY_ENABLED'] = 'false'
            if 'PREFECT_API_URL' not in env:
                env['PREFECT_API_URL'] = 'http://127.0.0.1:4200/api'
            
            result = subprocess.run(
                deploy_cmd,
                cwd=deploy_cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,  # 에러가 발생해도 예외를 발생시키지 않음
                env=env
            )
            
            # stdout 출력 (성공한 deployment 정보 포함)
            if result.stdout:
                print("📋 배포 출력:")
                print(result.stdout)
            
            # stderr 출력 (에러 정보 포함)
            if result.stderr:
                print("⚠️  배포 경고/에러:")
                print(result.stderr)
            
            # exit code 확인
            if result.returncode == 0:
                print("✅ 모든 deployment 배포 성공")
                return True
            else:
                print(f"⚠️  배포 종료 코드: {result.returncode}")
                print("💡 일부 deployment가 실패했을 수 있습니다.")
                print("   stdout/stderr 출력을 확인하여 어떤 deployment가 실패했는지 확인하세요.")
                print("   개별 배포 모드로 상세 에러를 확인하려면:")
                print("   export PREFECT_DEPLOY_INDIVIDUAL=1")
                
                # stdout에 "Successfully" 또는 "deployed"가 있으면 일부는 성공한 것
                if result.stdout and ("Successfully" in result.stdout or "deployed" in result.stdout.lower()):
                    print("✅ 일부 deployment는 성공했습니다.")
                    return True
                else:
                    return False
                    
        except Exception as e:
            print(f"❌ 배포 실행 중 예외 발생: {e}")
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
