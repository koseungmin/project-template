# 📄 통합 문서 처리 시스템

FastAPI Backend와 Prefect 기반 문서 임베딩 파이프라인을 통합한 AI 문서 처리 시스템입니다.

## 🏗️ 프로젝트 구조

```
skon/
├── 📦 shared_document_models/     # 공통 문서 모델 및 서비스
├── 🚀 fastapi-ai-chat-template/   # FastAPI 백엔드 서버
├── 🔄 prefect_template/           # Prefect 기반 문서 처리 파이프라인
├── 🔧 .vscode/                    # 통합 VSCode 설정
├── 📋 README.md                   # 이 파일
└── 🔐 .env.example               # 환경변수 템플릿
```

## ✨ 주요 특징

### 🔗 공통 모듈 아키텍처
- **중복 제거**: Document, DocumentChunk, ProcessingJob 모델 통합
- **재사용성**: CRUD, Service 레이어 공통화
- **일관성**: 두 프로젝트 간 데이터 모델 동기화

### 🚀 FastAPI Backend
- **문서 업로드**: 파일 업로드 및 메타데이터 관리
- **권한 관리**: 사용자별 문서 접근 제어
- **API 서비스**: RESTful API를 통한 문서 관리

### 🔄 Prefect Pipeline
- **자동 처리**: PDF 문서 자동 텍스트 추출 및 임베딩
- **이미지 분석**: GPT Vision을 통한 이미지 설명 생성
- **벡터 저장**: Milvus를 통한 벡터 데이터베이스 구축

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 필요한 설정값 입력
```

### 2. 의존성 설치

VSCode에서 `Ctrl+Shift+P` → `Tasks: Run Task` → `Install All Dependencies` 실행

또는 수동으로:

```bash
# 공통 모듈 의존성
pip install -r shared_document_models/requirements.txt

# Backend 의존성
pip install -r fastapi-ai-chat-template/app/backend/requirements.txt

# Prefect 의존성
pip install -r prefect_template/pre-fact-dcoument-embedding-template/requirements.txt
```

### 3. 서비스 실행

VSCode에서 `Ctrl+Shift+P` → `Tasks: Run Task` → `Start All Services` 실행

또는 개별 실행:

```bash
# 터미널 1: FastAPI Backend
cd fastapi-ai-chat-template/app/backend
python -m uvicorn ai_backend.main:app --host 0.0.0.0 --port 8000 --reload

# 터미널 2: Prefect Server
cd prefect_template/pre-fact-dcoument-embedding-template
python base/start_prefect_server.py

# 터미널 3: Prefect Worker
cd prefect_template/pre-fact-dcoument-embedding-template
python base/start_worker.py
```

## 🔧 개발 환경

### VSCode 설정
- **디버깅**: 각 서비스별 디버그 구성 제공
- **태스크**: 의존성 설치, 서비스 실행 등 자동화
- **확장**: Python, Docker, Kubernetes 등 권장 확장 프로그램

### 환경변수

주요 환경변수들:

```bash
# 데이터베이스
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=document_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Azure OpenAI
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

## 📊 서비스 접근

- **FastAPI Backend**: http://localhost:8000
  - API 문서: http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc

- **Prefect UI**: http://localhost:4200
  - 파이프라인 모니터링 및 실행

## 🔄 워크플로우

### 문서 처리 과정

1. **업로드**: FastAPI를 통해 문서 업로드
2. **메타데이터**: 공통 모듈로 문서 정보 저장
3. **처리**: Prefect 파이프라인으로 자동 처리
   - 텍스트 추출
   - 이미지 캡처 및 GPT 분석
   - 벡터 임베딩 생성
   - Milvus에 저장
4. **검색**: 임베딩 기반 의미 검색

## 🛠️ 개발 가이드

### 공통 모듈 사용

```python
# 공통 모델 사용
from shared_document_models import Document, DocumentService

# 데이터베이스 세션
from shared_document_models import get_db_session

with next(get_db_session()) as db:
    doc_service = DocumentService(db)
    result = doc_service.create_document_from_path(...)
```

### 새 기능 추가

1. **모델 변경**: `shared_document_models/models.py` 수정
2. **CRUD 추가**: `shared_document_models/crud.py` 확장
3. **서비스 로직**: `shared_document_models/services.py` 확장
4. **Backend API**: FastAPI 라우터 추가
5. **Prefect 태스크**: 파이프라인 태스크 추가

## 📚 문서

- [공통 모듈 가이드](shared_document_models/README.md)
- [FastAPI Backend 가이드](fastapi-ai-chat-template/README.md)
- [Prefect Pipeline 가이드](prefect_template/pre-fact-dcoument-embedding-template/README.md)

## 🤝 기여

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 라이선스

MIT License - 자세한 내용은 LICENSE 파일을 참조하세요.

## 🆘 지원

문제가 있거나 질문이 있으시면 Issue를 생성해 주세요.
