# Prefect 시스템 Kubernetes 배포 가이드

이 폴더는 launch.json의 1,2,3,4 단계를 Kubernetes 환경에서 실행하기 위한 설정 파일들을 포함합니다.

## 📁 파일 구조

```
k8s/
├── namespace.yaml                    # 네임스페이스 정의
├── configmap.yaml                    # 환경 설정
├── secrets.yaml                      # 민감한 정보 (API 키 등)
├── milvus-deployment.yaml           # Milvus, MinIO, etcd 배포
├── 1-prefect-server-deployment.yaml # 1단계: Prefect 서버
├── 2-flow-registration-job.yaml     # 2단계: Flow 등록
├── 3-prefect-worker-deployment.yaml # 3단계: Worker 시작
├── 4-pipeline-deployment-job.yaml   # 4단계: 파이프라인 배포
├── deploy.sh                         # 전체 배포 스크립트
├── cleanup.sh                        # 리소스 정리 스크립트
└── README.md                         # 이 파일
```

## 🚀 배포 방법

### 사전 요구사항
- Kubernetes 클러스터 (minikube, kind, 또는 클라우드)
- kubectl 명령어 도구
- Docker 이미지 빌드 환경

### 1. Docker 이미지 빌드
```bash
# Python 애플리케이션 이미지 빌드
docker build -t prefect-python-app:latest .
```

### 2. 시크릿 설정
```bash
# secrets.yaml 파일에서 실제 API 키로 수정
# 또는 kubectl로 직접 생성
kubectl create secret generic prefect-secrets \
  --from-literal=azure-openai-api-key="your-actual-api-key" \
  --from-literal=azure-openai-endpoint="your-endpoint" \
  --from-literal=azure-openai-deployment="your-deployment" \
  --from-literal=azure-openai-version="your-version" \
  -n prefect-system
```

### 3. 전체 배포 실행
```bash
# 실행 권한 부여
chmod +x deploy.sh

# 배포 실행
./deploy.sh
```

### 4. 개별 단계 배포
```bash
# 1단계: Prefect 서버
kubectl apply -f 1-prefect-server-deployment.yaml

# 2단계: Flow 등록
kubectl apply -f 2-flow-registration-job.yaml

# 3단계: Worker 시작
kubectl apply -f 3-prefect-worker-deployment.yaml

# 4단계: 파이프라인 배포
kubectl apply -f 4-pipeline-deployment-job.yaml
```

## 🔍 모니터링

### 상태 확인
```bash
# 전체 리소스 상태
kubectl get all -n prefect-system

# 특정 애플리케이션 상태
kubectl get pods -l app=prefect-server -n prefect-system
kubectl get pods -l app=prefect-worker -n prefect-system
kubectl get pods -l app=milvus-standalone -n prefect-system
```

### 로그 확인
```bash
# Prefect 서버 로그
kubectl logs -f -l app=prefect-server -n prefect-system

# Worker 로그
kubectl logs -f -l app=prefect-worker -n prefect-system

# Milvus 로그
kubectl logs -f -l app=milvus-standalone -n prefect-system
```

### Prefect UI 접속
```bash
# 포트 포워딩
kubectl port-forward -n prefect-system svc/prefect-server 4201:4201

# 브라우저에서 http://localhost:4201 접속
```

## 🧹 정리

### 전체 리소스 정리
```bash
chmod +x cleanup.sh
./cleanup.sh
```

### 개별 리소스 삭제
```bash
# 특정 단계만 삭제
kubectl delete -f 4-pipeline-deployment-job.yaml
kubectl delete -f 3-prefect-worker-deployment.yaml
kubectl delete -f 2-flow-registration-job.yaml
kubectl delete -f 1-prefect-server-deployment.yaml

# 네임스페이스 전체 삭제
kubectl delete namespace prefect-system
```

## ⚠️ 주의사항

1. **API 키 보안**: secrets.yaml의 API 키를 실제 값으로 변경
2. **이미지 태그**: Docker 이미지 태그를 실제 빌드된 이미지로 변경
3. **리소스 제한**: 프로덕션 환경에서는 리소스 요청/제한 조정
4. **데이터 영속성**: PVC를 사용하여 데이터 영속성 보장
5. **네트워크 정책**: 프로덕션 환경에서는 네트워크 정책 추가 고려
6. **Work Pool 이름 일치**: `k8s-pool` 이름이 모든 설정에서 일치해야 함
   - prefect-k8s.yaml의 `work_pool.name`
   - Work Pool 생성 시 이름
   - Worker 시작 시 `--pool` 파라미터

## 🔧 커스터마이징

### 리소스 조정
- `replicas`: 워커 수 조정
- `resources.requests/limits`: CPU/메모리 조정
- `storage`: PVC 스토리지 크기 조정

### 환경 변수 추가
- `configmap.yaml`: 새로운 환경 변수 추가
- `secrets.yaml`: 새로운 시크릿 추가

### 헬스체크 조정
- `livenessProbe`: 생존성 검사 설정
- `readinessProbe`: 준비성 검사 설정

## 📚 참고 자료

- [Prefect Kubernetes 배포](https://docs.prefect.io/2.0/guides/deployment/kubernetes/)
- [Milvus Kubernetes 가이드](https://milvus.io/docs/install_standalone-docker.md)
- [Kubernetes 공식 문서](https://kubernetes.io/docs/) 