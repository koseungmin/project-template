#!/bin/bash

# Prefect 시스템을 Kubernetes에 배포하는 스크립트
# launch.json의 1,2,3,4 단계를 순차적으로 실행

set -e  # 에러 발생 시 스크립트 중단

NAMESPACE="prefect-system"
TIMEOUT=300  # 5분 타임아웃

echo "🚀 Prefect 시스템 Kubernetes 배포 시작..."

# 1. 네임스페이스 생성
echo "📁 1단계: 네임스페이스 생성"
kubectl apply -f namespace.yaml
echo "✅ 네임스페이스 생성 완료"

# 2. 설정 및 시크릿 적용
echo "🔧 2단계: 설정 및 시크릿 적용"
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
echo "✅ 설정 및 시크릿 적용 완료"

# 3. ServiceAccount 및 RBAC 설정
echo "🔐 3단계: ServiceAccount 및 RBAC 설정"
kubectl apply -f service-account.yaml
echo "✅ ServiceAccount 및 RBAC 설정 완료"

# 4. Milvus 인프라 배포
echo "🏗️ 4단계: Milvus 인프라 배포"
kubectl apply -f milvus-deployment.yaml
echo "✅ Milvus 인프라 배포 완료"

# 5. Milvus 서비스 준비 대기
echo "⏳ 5단계: Milvus 서비스 준비 대기"
echo "   - etcd 준비 대기 중..."
kubectl wait --for=condition=ready pod -l app=milvus-etcd -n $NAMESPACE --timeout=${TIMEOUT}s
echo "   - MinIO 준비 대기 중..."
kubectl wait --for=condition=ready pod -l app=milvus-minio -n $NAMESPACE --timeout=${TIMEOUT}s
echo "   - Milvus 준비 대기 중..."
kubectl wait --for=condition=ready pod -l app=milvus-standalone -n $NAMESPACE --timeout=${TIMEOUT}s
echo "✅ Milvus 서비스 준비 완료"

# 6. Prefect 서버 배포 (1단계)
echo "🌐 6단계: Prefect 서버 배포 (1단계)"
kubectl apply -f 1-prefect-server-deployment.yaml
echo "✅ Prefect 서버 배포 완료"

# 7. Prefect 서버 준비 대기
echo "⏳ 7단계: Prefect 서버 준비 대기"
kubectl wait --for=condition=ready pod -l app=prefect-server -n $NAMESPACE --timeout=${TIMEOUT}s
echo "✅ Prefect 서버 준비 완료"

# 8. Flow 등록 (2단계)
echo "📝 8단계: Flow 등록 (2단계)"
kubectl apply -f 2-flow-registration-job.yaml
echo "✅ Flow 등록 Job 생성 완료"

# 9. Flow 등록 완료 대기
echo "⏳ 9단계: Flow 등록 완료 대기"
kubectl wait --for=condition=complete job/flow-registration -n $NAMESPACE --timeout=${TIMEOUT}s
echo "✅ Flow 등록 완료"

# 10. Worker 시작 (3단계)
echo "👷 10단계: Worker 시작 (3단계)"
kubectl apply -f 3-prefect-worker-deployment.yaml
echo "✅ Worker 배포 완료"

# 11. Worker 준비 대기
echo "⏳ 11단계: Worker 준비 대기"
kubectl wait --for=condition=ready pod -l app=prefect-worker -n $NAMESPACE --timeout=${TIMEOUT}s
echo "✅ Worker 준비 완료"

# 12. 파이프라인 배포 (4단계)
echo "🚀 12단계: 파이프라인 배포 (4단계)"
kubectl apply -f 4-pipeline-deployment-job.yaml
echo "✅ 파이프라인 배포 Job 생성 완료"

# 13. 파이프라인 배포 완료 대기
echo "⏳ 13단계: 파이프라인 배포 완료 대기"
kubectl wait --for=condition=complete job/pipeline-deployment -n $NAMESPACE --timeout=${TIMEOUT}s
echo "✅ 파이프라인 배포 완료"

# 14. Prefect 배포 설정 적용
echo "📋 14단계: Prefect 배포 설정 적용"

# Work Pool 생성 (k8s-pool)
echo "   - Work Pool 'k8s-pool' 생성 중..."
kubectl exec -it -n $NAMESPACE deployment/prefect-server -- \
  prefect work-pool create k8s-pool --type kubernetes --yes

# 배포 설정 적용
echo "   - 배포 설정 적용 중..."
kubectl exec -it -n $NAMESPACE deployment/prefect-server -- \
  prefect deployment apply prefect-k8s.yaml

echo "✅ Prefect 배포 설정 적용 완료"

# 15. 배포 상태 확인
echo "📊 15단계: 배포 상태 확인"
echo ""
echo "=== 배포된 리소스 상태 ==="
kubectl get all -n $NAMESPACE
echo ""
echo "=== Prefect 서버 상태 ==="
kubectl get pods -l app=prefect-server -n $NAMESPACE
echo ""
echo "=== Worker 상태 ==="
kubectl get pods -l app=prefect-worker -n $NAMESPACE
echo ""
echo "=== Milvus 상태 ==="
kubectl get pods -l app=milvus-standalone -n $NAMESPACE

echo ""
echo "🎉 모든 단계 배포 완료!"
echo ""
echo "📱 Prefect UI 접속:"
echo "   kubectl port-forward -n $NAMESPACE svc/prefect-server 4201:4201"
echo "   브라우저에서 http://localhost:4201 접속"
echo ""
echo "🔍 로그 확인:"
echo "   Prefect 서버: kubectl logs -f -l app=prefect-server -n $NAMESPACE"
echo "   Worker: kubectl logs -f -l app=prefect-worker -n $NAMESPACE"
echo "   Milvus: kubectl logs -f -l app=milvus-standalone -n $NAMESPACE"
echo ""
echo "📋 다음 단계:"
echo "   1. Prefect CLI로 배포 설정 적용:"
echo "      kubectl exec -it -n $NAMESPACE deployment/prefect-server -- prefect deployment apply prefect-k8s.yaml"
echo "   2. Work Pool 생성:"
echo "      kubectl exec -it -n $NAMESPACE deployment/prefect-server -- prefect work-pool create k8s-pool --type kubernetes" 