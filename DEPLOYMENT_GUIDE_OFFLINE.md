# 폐쇄망 환경 배포 가이드

이 가이드는 폐쇄망 환경에서 chat-api와 doc-processor 서비스를 Kubernetes에 배포하는 방법을 설명합니다.

## 🚨 중요 사항

- **폐쇄망 환경**에서는 인터넷 접속이 불가능하므로 `pip install`을 사용할 수 없습니다.
- **wheel 파일 기반 설치**: 기존 `venv_py312`의 패키지들을 wheel 파일로 다운로드하여 Docker 이미지에 포함시킵니다.
- 모든 Docker 이미지는 로컬에서 빌드되며, `imagePullPolicy: Never`로 설정됩니다.
- 경로 문제를 방지하기 위해 wheel 파일 방식을 사용합니다.

## 📋 사전 준비사항

### 1. 환경 확인
```bash
# Docker 설치 확인
docker --version

# Kubernetes 클러스터 확인
kubectl cluster-info

# venv 패키지 확인
ls -la chat-api/app/backend/venv_py312/lib/python3.12/site-packages/
ls -la doc-processor/venv_py312/lib/python3.12/site-packages/
```

### 2. 필요한 패키지들
각 서비스의 `venv_py312`에 다음 패키지들이 설치되어 있어야 합니다:

**chat-api 서비스:**
- fastapi, uvicorn, gunicorn
- sqlalchemy, psycopg2-binary
- openai, langchain, langserve
- redis, pydantic, pandas
- 기타 requirements.txt에 명시된 패키지들

**doc-processor 서비스:**
- prefect, python-dotenv
- psycopg2-binary, sqlalchemy
- pymilvus, milvus-lite
- openai, PyMuPDF, Pillow
- azure-search-documents
- 기타 requirements.txt에 명시된 패키지들

## 🚀 배포 과정

### 1. 자동 배포 (권장)
```bash
# 실행 권한 부여
chmod +x prepare-wheels.sh deploy-dev.sh

# wheel 파일 준비 (최초 1회만 실행)
./prepare-wheels.sh

# 배포 실행
./deploy-dev.sh
```

### 1-1. Wheel 파일 준비 (수동)
```bash
# 각 서비스의 wheel 파일을 수동으로 준비하는 경우
cd chat-api/app/backend
mkdir -p wheels
source venv_py312/bin/activate
pip download -r requirements.txt -d wheels
cd ../../..

cd doc-processor
mkdir -p wheels
source venv_py312/bin/activate
pip download -r requirements.txt -d wheels
cd ..
```

### 2. 수동 배포

#### Step 1: shared_core 복사
```bash
# shared_core를 각 서비스에 복사
cp -r shared_core chat-api/app/backend/
cp -r shared_core doc-processor/
```

#### Step 2: Wheel 파일 준비
```bash
# wheel 파일 준비 스크립트 실행
./prepare-wheels.sh
```

#### Step 3: Docker 이미지 빌드
```bash
# chat-api 이미지 빌드
cd chat-api/app/backend
# wheels 디렉토리와 requirements-freeze.txt가 존재하는지 확인
docker build -f Dockerfile.dev -t chat-api-dev:latest .
cd ../../..

# doc-processor 이미지 빌드
cd doc-processor
# wheels 디렉토리와 requirements-freeze.txt가 존재하는지 확인
docker build -f Dockerfile.dev -t doc-processor-dev:latest .
cd ..
```

#### Step 4: Kubernetes 리소스 배포
```bash
# 인프라 서비스 배포
kubectl apply -f k8s-infra/dev-postgres.yaml
kubectl apply -f k8s-infra/dev-redis.yaml
kubectl apply -f k8s-infra/dev-milvus.yaml

# 애플리케이션 서비스 배포
kubectl apply -f chat-api/app/backend/k8s/dev-deployment.yaml
kubectl apply -f chat-api/app/backend/k8s/dev-service.yaml
kubectl apply -f doc-processor/k8s/dev-deployment.yaml
kubectl apply -f doc-processor/k8s/dev-service.yaml
```

## 🔍 배포 확인

### 1. Pod 상태 확인
```bash
kubectl get pods -l environment=development
```

### 2. 서비스 상태 확인
```bash
kubectl get services -l environment=development
```

### 3. 로그 확인
```bash
# chat-api 로그
kubectl logs -f deployment/chat-api-dev

# doc-processor 로그
kubectl logs -f deployment/doc-processor-dev

# prefect-server 로그
kubectl logs -f deployment/prefect-server-dev
```

## 🌐 서비스 접속

### NodePort를 통한 외부 접속
- **chat-api**: http://localhost:30080
- **prefect-server UI**: http://localhost:30421
- **doc-processor**: http://localhost:30081

### Port Forwarding을 통한 접속
```bash
# chat-api 포트 포워딩
kubectl port-forward svc/chat-api-service 8000:8000

# prefect-server 포트 포워딩
kubectl port-forward svc/prefect-server-service 4201:4201

# doc-processor 포트 포워딩
kubectl port-forward svc/doc-processor-service 8001:8000
```

## 🛠️ 문제 해결

### 1. Wheel 파일 누락
```bash
# wheel 파일이 존재하지 않는 경우
print_error "wheel 파일들이 존재하지 않습니다. 먼저 ./prepare-wheels.sh를 실행해주세요."
```
**해결방법**: 
1. `./prepare-wheels.sh` 스크립트를 실행하여 wheel 파일들을 준비하세요.
2. 각 서비스의 `wheels/` 디렉토리에 `.whl` 파일들이 있는지 확인하세요.

### 2. venv 패키지 누락
```bash
# venv가 존재하지 않는 경우
print_error "venv_py312가 존재하지 않습니다. 먼저 venv를 설정해주세요."
```
**해결방법**: 각 서비스 디렉토리에서 venv를 생성하고 필요한 패키지들을 설치하세요.

### 3. Docker 이미지 빌드 실패
```bash
# 이미지 빌드 시 패키지 관련 오류
```
**해결방법**: 
- `wheels/` 디렉토리에 필요한 wheel 파일들이 모두 있는지 확인
- `requirements-freeze.txt` 파일이 올바르게 생성되었는지 확인
- shared_core가 올바르게 복사되었는지 확인

### 4. Pod 시작 실패
```bash
# Pod가 Running 상태가 되지 않는 경우
kubectl describe pod <pod-name>
```
**해결방법**:
- 로그를 확인하여 구체적인 오류 메시지 파악
- 환경 변수 설정 확인
- 볼륨 마운트 확인

### 5. 서비스 연결 실패
```bash
# 서비스 간 통신이 안 되는 경우
kubectl get endpoints
```
**해결방법**:
- 서비스의 selector가 올바른지 확인
- 네트워크 정책 확인
- DNS 해석 문제인지 확인

## 📁 파일 구조

```
project-template/
├── chat-api/
│   ├── app/backend/
│   │   ├── Dockerfile.dev          # chat-api Docker 파일
│   │   ├── venv_py312/            # Python 가상환경
│   │   ├── wheels/                # wheel 파일들 (폐쇄망용)
│   │   ├── requirements-freeze.txt # 패키지 목록
│   │   └── k8s/
│   │       ├── dev-deployment.yaml # chat-api K8s 배포 파일
│   │       └── dev-service.yaml   # chat-api K8s 서비스 파일
│   └── shared_core/               # 복사된 공통 라이브러리
├── doc-processor/
│   ├── Dockerfile.dev             # doc-processor Docker 파일
│   ├── venv_py312/               # Python 가상환경
│   ├── wheels/                   # wheel 파일들 (폐쇄망용)
│   ├── requirements-freeze.txt   # 패키지 목록
│   ├── shared_core/              # 복사된 공통 라이브러리
│   └── k8s/
│       ├── dev-deployment.yaml   # doc-processor K8s 배포 파일
│       └── dev-service.yaml     # doc-processor K8s 서비스 파일
├── shared_core/                  # 원본 공통 라이브러리
├── k8s-infra/                   # 인프라 K8s 파일들
│   ├── dev-postgres.yaml        # PostgreSQL 배포 파일
│   ├── dev-redis.yaml          # Redis 배포 파일
│   └── dev-milvus.yaml         # Milvus 배포 파일
├── prepare-wheels.sh           # wheel 파일 준비 스크립트
└── deploy-dev.sh               # 자동 배포 스크립트
```

## 🔄 업데이트 및 재배포

### 코드 변경 시
```bash
# 코드 변경 후 재빌드 및 재배포
./deploy-dev.sh
```

### 패키지 업데이트 시
```bash
# 1. 로컬에서 패키지 업데이트
# 2. venv 재생성 또는 패키지 재설치
# 3. wheel 파일 재생성
./prepare-wheels.sh
# 4. Docker 이미지 재빌드
# 5. Kubernetes 리소스 재배포
```

## 📞 지원

배포 과정에서 문제가 발생하면 다음을 확인하세요:

1. **로그 확인**: `kubectl logs -f deployment/<deployment-name>`
2. **이벤트 확인**: `kubectl get events --sort-by=.metadata.creationTimestamp`
3. **리소스 상태**: `kubectl describe pod <pod-name>`
4. **네트워크 연결**: `kubectl exec -it <pod-name> -- /bin/bash`

---

이 가이드를 따라하면 폐쇄망 환경에서도 안정적으로 서비스를 배포할 수 있습니다.
