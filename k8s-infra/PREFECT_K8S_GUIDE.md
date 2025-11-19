# Prefect Kubernetes 배포 가이드

## 문제점

현재 단일 컨테이너에 Prefect 서버와 워커를 모두 넣어서 사용하는 방식은:
- 서브프로세스 관리 문제
- 워커와 서버가 독립적으로 스케일링 불가
- 배포 작업이 서버 프로세스를 방해
- Prefect 공식 권장 방식과 다름

## Prefect 공식 권장 방식

Prefect는 Kubernetes에서 **서버와 워커를 분리**하여 배포하는 것을 권장합니다:

1. **Prefect Server**: 별도 Deployment로 배포
2. **Prefect Worker**: 별도 Deployment로 배포 (스케일링 가능)
3. **Deployment 작업**: Job 또는 Init Container로 실행

## 배포 구조

```
┌─────────────────────────────────────────┐
│  Prefect Server Deployment              │
│  - prefect server start                 │
│  - Service: prefect-server:4200         │
└─────────────────────────────────────────┘
              ↑
              │ API 호출
              │
┌─────────────────────────────────────────┐
│  Prefect Worker Deployment              │
│  - prefect worker start --pool default  │
│  - 여러 개 스케일링 가능                │
└─────────────────────────────────────────┘
              ↑
              │ 작업 실행
              │
┌─────────────────────────────────────────┐
│  Deployment Job (한 번만 실행)          │
│  - prefect deploy --all                 │
│  - 완료 후 종료                         │
└─────────────────────────────────────────┘
```

## 배포 순서

### 1. Prefect Server 배포

```bash
kubectl apply -f k8s-infra/prefect-server-deployment.yaml
```

서버가 시작되면:
- `prefect-server` Service를 통해 접근 가능
- 내부: `http://prefect-server:4200/api`
- 외부: Ingress를 통해 `https://aiagent.com/scheduler`

### 2. Work Pool 생성

서버가 시작된 후, Work Pool을 생성해야 합니다:

**방법 A: Init Container 사용**
```yaml
initContainers:
- name: create-work-pool
  image: your-registry/prefect-doc-processor:latest
  command: ["sh", "-c", "prefect work-pool create default --type process || true"]
  env:
  - name: PREFECT_API_URL
    value: "http://prefect-server:4200/scheduler/api"
```

**방법 B: 별도 Job으로 실행**
```bash
kubectl run create-work-pool --image=your-registry/prefect-doc-processor:latest \
  --restart=Never --rm -it -- \
  sh -c "prefect work-pool create default --type process || true"
```

**방법 C: UI에서 생성** (가장 간단)
- 브라우저에서 `https://aiagent.com/scheduler` 접속
- Work Pools 메뉴에서 생성

### 3. Prefect Worker 배포

```bash
kubectl apply -f k8s-infra/prefect-worker-deployment.yaml
```

워커는 여러 개 배포 가능:
```bash
kubectl scale deployment prefect-worker --replicas=3
```

### 4. Deployment 배포 (한 번만)

```bash
kubectl apply -f k8s-infra/prefect-deployment-job.yaml
```

또는 수동으로:
```bash
kubectl run prefect-deploy --image=your-registry/prefect-doc-processor:latest \
  --restart=Never --rm -it -- \
  python3 /app/base/deploy_pipeline.py
```

## 환경변수 설정

### Prefect Server
- `PREFECT_API_URL`: 내부에서 사용 (워커/배포용)
- `PREFECT_SERVER_API_BASE_PATH`: `/scheduler/api`
- `PREFECT_UI_SERVE_BASE`: `/scheduler`

### Prefect Worker
- `PREFECT_API_URL`: `http://prefect-server:4200/scheduler/api` (Service 이름 사용)
- `PREFECT_WORK_POOL`: `default`
- `PREFECT_WORK_QUEUE`: `default`

### Deployment Job
- `PREFECT_API_URL`: `http://prefect-server:4200/scheduler/api`
- `PREFECT_YAML_PATH`: `/app/base/prefect.yaml`

## Ingress 설정

Prefect Server를 외부에 노출:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: prefect-ingress
  annotations:
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
  - host: aiagent.com
    http:
      paths:
      - path: /scheduler/api(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: prefect-server
            port:
              number: 4200
      - path: /scheduler(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: prefect-server
            port:
              number: 4200
```

## 장점

1. **독립적 스케일링**: 서버와 워커를 각각 스케일링 가능
2. **안정성**: 서버와 워커가 서로 영향을 주지 않음
3. **관리 용이**: 각 컴포넌트를 독립적으로 관리
4. **Prefect 권장 방식**: 공식 문서와 일치

## 모니터링

```bash
# 서버 상태 확인
kubectl get pods -l app=prefect-server

# 워커 상태 확인
kubectl get pods -l app=prefect-worker

# 로그 확인
kubectl logs -l app=prefect-server
kubectl logs -l app=prefect-worker

# 배포 Job 상태
kubectl get jobs
kubectl logs job/prefect-deploy
```

## 트러블슈팅

### 워커가 서버에 연결하지 못함
- `PREFECT_API_URL`이 `http://prefect-server:4200/scheduler/api`인지 확인
- Service 이름이 올바른지 확인: `kubectl get svc prefect-server`

### 배포가 실행되지 않음
- Work Pool이 생성되었는지 확인
- Worker가 실행 중인지 확인
- `prefect deployment ls`로 deployment가 생성되었는지 확인

### 서버가 응답하지 않음
- 서버 Pod가 Running 상태인지 확인
- 서버 로그 확인: `kubectl logs -l app=prefect-server`


