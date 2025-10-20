#!/bin/bash

# 폐쇄망 환경용 wheel 파일 준비 스크립트

set -e

echo "🔧 폐쇄망 환경용 wheel 파일을 준비합니다..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수 정의
print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# chat-api wheel 파일 준비
print_step "chat-api 서비스용 wheel 파일을 준비합니다..."
cd chat-api/app/backend

# wheels 디렉토리 생성
mkdir -p wheels

# venv 활성화 후 wheel 파일 다운로드
if [ -d "venv_py312" ]; then
    source venv_py312/bin/activate
    
    # requirements.txt 기반으로 wheel 파일 다운로드
    pip download -r requirements.txt -d wheels --no-deps
    
    # 의존성도 함께 다운로드
    pip download -r requirements.txt -d wheels
    
    print_step "chat-api wheel 파일 준비 완료: $(ls wheels/*.whl | wc -l)개 파일"
else
    print_error "venv_py312가 존재하지 않습니다."
    exit 1
fi

cd ../../..

# doc-processor wheel 파일 준비
print_step "doc-processor 서비스용 wheel 파일을 준비합니다..."
cd doc-processor

# wheels 디렉토리 생성
mkdir -p wheels

# venv 활성화 후 wheel 파일 다운로드
if [ -d "venv_py312" ]; then
    source venv_py312/bin/activate
    
    # requirements.txt 기반으로 wheel 파일 다운로드
    pip download -r requirements.txt -d wheels --no-deps
    
    # 의존성도 함께 다운로드
    pip download -r requirements.txt -d wheels
    
    print_step "doc-processor wheel 파일 준비 완료: $(ls wheels/*.whl | wc -l)개 파일"
else
    print_error "venv_py312가 존재하지 않습니다."
    exit 1
fi

cd ..

# shared_core wheel 파일 준비 (필요한 경우)
print_step "shared_core 라이브러리용 wheel 파일을 준비합니다..."
cd shared_core

# wheels 디렉토리 생성
mkdir -p wheels

if [ -f "requirements.txt" ]; then
    # venv가 있다면 사용, 없다면 시스템 pip 사용
    if [ -d "venv_py312" ]; then
        source venv_py312/bin/activate
    fi
    
    pip download -r requirements.txt -d wheels
    
    print_step "shared_core wheel 파일 준비 완료: $(ls wheels/*.whl | wc -l)개 파일"
fi

cd ..

echo ""
echo "🎉 모든 wheel 파일 준비가 완료되었습니다!"
echo ""
echo "생성된 wheel 파일들:"
echo "  - chat-api/app/backend/wheels/ ($(ls chat-api/app/backend/wheels/*.whl 2>/dev/null | wc -l)개 파일)"
echo "  - doc-processor/wheels/ ($(ls doc-processor/wheels/*.whl 2>/dev/null | wc -l)개 파일)"
echo "  - shared_core/wheels/ ($(ls shared_core/wheels/*.whl 2>/dev/null | wc -l)개 파일)"
echo ""
echo "이제 ./deploy-dev.sh를 실행하여 배포할 수 있습니다."
