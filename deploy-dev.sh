#!/bin/bash

# 개발서버 배포 스크립트
# 폐쇄망 환경에서 사용

set -e

echo "🚀 개발서버 배포를 시작합니다..."

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

# 0. Wheel 파일 준비 (폐쇄망 환경)
print_step "폐쇄망 환경용 wheel 파일을 준비합니다..."
if [ ! -f "prepare-wheels.sh" ]; then
    print_error "prepare-wheels.sh 파일이 없습니다."
    exit 1
fi

chmod +x prepare-wheels.sh
./prepare-wheels.sh

# 1. Docker 이미지 빌드 (폐쇄망 환경)
print_step "Docker 이미지를 빌드합니다..."

# shared_core를 각 서비스에 복사
echo "shared_core를 chat-api에 복사합니다..."
cp -r shared_core chat-api/app/backend/

echo "shared_core를 doc-processor에 복사합니다..."
cp -r shared_core doc-processor/

# chat-api Docker 이미지 빌드 (폐쇄망 환경)
print_step "chat-api Docker 이미지를 빌드합니다..."
cd chat-api/app/backend
# wheel 파일들이 존재하는지 확인
if [ ! -d "wheels" ] || [ ! "$(ls -A wheels/*.whl 2>/dev/null)" ]; then
    print_error "wheel 파일들이 존재하지 않습니다. 먼저 ./prepare-wheels.sh를 실행해주세요."
    exit 1
fi
docker build -f Dockerfile.dev -t chat-api-dev:latest .
cd ../../..

# doc-processor Docker 이미지 빌드 (폐쇄망 환경)
print_step "doc-processor Docker 이미지를 빌드합니다..."
cd doc-processor
# wheel 파일들이 존재하는지 확인
if [ ! -d "wheels" ] || [ ! "$(ls -A wheels/*.whl 2>/dev/null)" ]; then
    print_error "wheel 파일들이 존재하지 않습니다. 먼저 ./prepare-wheels.sh를 실행해주세요."
    exit 1
fi
docker build -f Dockerfile.dev -t doc-processor-dev:latest .
cd ..

# 2. Kubernetes 리소스 배포
print_step "Kubernetes 리소스를 배포합니다..."

# 인프라 서비스 배포 (PostgreSQL, Redis, Milvus)
print_step "인프라 서비스를 배포합니다..."
kubectl apply -f k8s-infra/dev-postgres.yaml
kubectl apply -f k8s-infra/dev-redis.yaml
kubectl apply -f k8s-infra/dev-milvus.yaml

# 인프라 서비스가 준비될 때까지 대기
print_step "인프라 서비스가 준비될 때까지 대기합니다..."
kubectl wait --for=condition=ready pod -l app=postgres,environment=development --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis,environment=development --timeout=120s
kubectl wait --for=condition=ready pod -l app=milvus,environment=development --timeout=120s

# 애플리케이션 서비스 배포
print_step "애플리케이션 서비스를 배포합니다..."

# chat-api 배포
kubectl apply -f chat-api/app/backend/k8s/dev-deployment.yaml
kubectl apply -f chat-api/app/backend/k8s/dev-service.yaml

# doc-processor 배포
kubectl apply -f doc-processor/k8s/dev-deployment.yaml
kubectl apply -f doc-processor/k8s/dev-service.yaml

# 애플리케이션이 준비될 때까지 대기
print_step "애플리케이션이 준비될 때까지 대기합니다..."
kubectl wait --for=condition=ready pod -l app=chat-api,environment=development --timeout=120s
kubectl wait --for=condition=ready pod -l app=prefect-server,environment=development --timeout=120s
kubectl wait --for=condition=ready pod -l app=doc-processor,environment=development --timeout=120s

# 3. 배포 상태 확인
print_step "배포 상태를 확인합니다..."
kubectl get pods -l environment=development
kubectl get services -l environment=development

echo ""
echo "🎉 개발서버 배포가 완료되었습니다!"
echo ""
echo "서비스 접속 정보:"
echo "  - chat-api: http://localhost:30080"
echo "  - prefect-server UI: http://localhost:30421"
echo "  - doc-processor: http://localhost:30081"
echo ""
echo "포트 포워딩 명령어:"
echo "  kubectl port-forward svc/chat-api-service 8000:8000"
echo "  kubectl port-forward svc/prefect-server-service 4201:4201"
echo "  kubectl port-forward svc/doc-processor-service 8001:8000"
echo ""
echo "로그 확인 명령어:"
echo "  kubectl logs -f deployment/chat-api-dev"
echo "  kubectl logs -f deployment/doc-processor-dev"
echo "  kubectl logs -f deployment/prefect-server-dev"
