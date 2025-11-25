# Common Backend

암복호화 공통 서비스를 제공하는 FastAPI 기반 백엔드 서비스입니다.

## 개요

`common_backend`는 암복호화 기능을 제공하는 공통 서비스로, `ai_backend`와 동일한 구조와 로깅/예외 처리 방식을 사용합니다.

## 주요 기능

- 암호화/복호화 API 제공
- JWT 인증 미들웨어 (선택사항)
- 통합 로깅 시스템
- 글로벌 예외 처리
- CORS 지원

## 프로젝트 구조

```
common_backend/
├── src/
│   ├── api/
│   │   ├── routers/          # API 라우터
│   │   │   └── crypto_router.py
│   │   └── services/         # 비즈니스 로직 서비스
│   │       └── crypto_service.py
│   ├── config/                # 설정 관리
│   │   └── simple_settings.py
│   ├── core/                  # 핵심 기능
│   │   ├── dependencies.py
│   │   └── global_exception_handlers.py
│   ├── middleware/            # 미들웨어
│   │   └── auth_middleware.py
│   ├── types/                 # 타입 정의
│   │   ├── request/
│   │   └── response/
│   ├── utils/                 # 유틸리티
│   │   └── logging_utils.py
│   └── main.py               # 애플리케이션 진입점
├── logs/                     # 로그 파일 (자동 생성)
├── requirements.txt          # Python 의존성
├── k8s-network-policy-example.yaml  # Kubernetes 네트워크 정책 예시
└── README.md
```

## 설치 및 실행

### 1. 의존성 설치

```bash
cd common_backend
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 필요한 설정을 추가하세요:

```bash
# .env 파일 예시 (클러스터 내부 전용)
APP_LOG_LEVEL=info
SERVER_PORT=8001
JWT_ENABLED=false  # 클러스터 내부 전용이면 false (기본값)
CRYPTO_ALGORITHM=AES-256-GCM

# JWT 인증이 필요한 경우에만 추가
# JWT_ENABLED=true
# JWT_SECRET_KEY=your-secret-key-here
```

### 3. 서버 실행

```bash
# 개발 모드
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

# 프로덕션 모드
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

## API 엔드포인트

### 암호화

```bash
POST /v1/crypto/encrypt
Content-Type: application/json

{
  "data": "암호화할 데이터",
  "algorithm": "AES-256-GCM"  # 선택사항
}
```

### 복호화

```bash
POST /v1/crypto/decrypt
Content-Type: application/json

{
  "encrypted_data": "암호화된 데이터",
  "algorithm": "AES-256-GCM"  # 선택사항
}
```

### Health Check

```bash
GET /health
```

## 암복호화 구현

현재 `crypto_service.py`는 예시 구현만 포함되어 있습니다. 실제 암복호화 로직은 다음 위치에서 구현하세요:

- `src/api/services/crypto_service.py`의 `encrypt()` 및 `decrypt()` 메서드

## 환경 변수

주요 환경 변수 목록:

- `APP_LOG_LEVEL`: 애플리케이션 로그 레벨 (default: info)
- `SERVER_PORT`: 서버 포트 (default: 8001)
- `JWT_ENABLED`: JWT 인증 활성화 여부 (default: false, 클러스터 내부 전용)
- `JWT_SECRET_KEY`: JWT 서명 키 (JWT_ENABLED=true인 경우 필요)
- `CRYPTO_ALGORITHM`: 암호화 알고리즘 (default: AES-256-GCM)
- `LOG_TO_FILE`: 파일 로깅 활성화 여부 (default: false)
- `LOG_DIR`: 로그 파일 디렉토리 (default: ./logs)

자세한 설정은 `src/config/simple_settings.py`를 참조하세요.

## 보안 고려사항

### 클러스터 내부 전용 서비스 (권장)

이 서비스는 기본적으로 **클러스터 내부에서만 호출**되도록 설계되었습니다:

1. **JWT 인증 비활성화** (기본값: `JWT_ENABLED=false`)
   - 클러스터 내부 파드 간 통신은 네트워크 정책으로 보안 관리
   - CoreDNS를 통한 내부 DNS 호출만 허용
   - **보안 위배가 아닙니다** - 적절한 네트워크 정책과 함께 사용 시 안전합니다

2. **Kubernetes 네트워크 정책** (필수)
   - `k8s-network-policy-example.yaml` 파일 참조
   - 특정 네임스페이스/파드에서만 접근 허용하도록 설정
   - Service는 `ClusterIP` 타입으로 내부 전용 설정
   - Ingress는 내부 DNS만 제공 (외부 노출 없음)

3. **추가 보안 조치**
   - RBAC 설정 (최소 권한 원칙)
   - Pod Security Standards 적용
   - 서비스 메시(mTLS) 사용 고려 (선택사항)

> 📖 **자세한 보안 가이드**: `SECURITY.md` 파일 참조

### JWT 인증이 필요한 경우

외부에서도 접근해야 하거나 추가 인증이 필요한 경우:
- `JWT_ENABLED=true`로 설정
- `JWT_SECRET_KEY` 설정
- 라우터에서 `get_current_user_id` 의존성 주석 해제

## 로깅

`ai_backend`와 동일한 로깅 시스템을 사용합니다:

- 콘솔 로그: 항상 활성화
- 파일 로그: `LOG_TO_FILE=true`로 활성화
- 로그 로테이션: `LOG_ROTATION` 설정에 따라 daily/weekly/monthly/size
- 로그 보관: `LOG_RETENTION_DAYS` 설정에 따라 자동 정리

## 예외 처리

모든 예외는 `HandledException` 또는 `UnHandledException`으로 처리되며, 일관된 에러 응답 형식을 제공합니다:

```json
{
  "code": -2001,
  "message": "암호화 중 오류가 발생했습니다.",
  "content": "요청 처리 중 오류가 발생했습니다: 암호화 중 오류가 발생했습니다.",
  "timestamp": "2025-01-20T10:30:00+09:00",
  "trace_id": "uuid-here"
}
```

## 개발 가이드

### 새로운 라우터 추가

1. `src/api/routers/`에 새 라우터 파일 생성
2. `src/main.py`의 `create_app()` 함수에서 라우터 등록

### 새로운 서비스 추가

1. `src/api/services/`에 새 서비스 파일 생성
2. `src/core/dependencies.py`에 의존성 함수 추가 (필요한 경우)
3. 라우터에서 서비스 사용

## 참고

- 이 서비스는 `ai_backend`의 구조를 기반으로 만들어졌습니다
- 암복호화 로직은 사용자가 직접 구현해야 합니다
- **기본적으로 클러스터 내부 전용 서비스**로 설계되었습니다 (JWT 비활성화)
- 외부 접근이 필요한 경우에만 `JWT_ENABLED=true`로 설정하세요
- 보안은 Kubernetes 네트워크 정책과 CoreDNS로 관리하는 것을 권장합니다

