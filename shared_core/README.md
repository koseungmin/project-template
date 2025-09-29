# 공통 문서 모델 패키지

Backend와 Prefect 프로젝트에서 공통으로 사용하는 문서 관련 모델, CRUD, 서비스를 제공하는 패키지입니다.

## 구조

```
shared_document_models/
├── __init__.py          # 패키지 초기화 및 공통 import
├── models.py            # SQLAlchemy 모델 정의
├── database.py          # 데이터베이스 연결 관리
├── crud.py              # CRUD 작업 클래스들
├── services.py          # 비즈니스 로직 서비스들
├── requirements.txt     # 패키지 의존성
└── README.md           # 이 파일
```

## 주요 구성요소

### 모델 (models.py)
- `Document`: 통합 문서 테이블
- `DocumentChunk`: 문서 청크 정보 테이블  
- `ProcessingJob`: 처리 작업 로그 테이블

### CRUD (crud.py)
- `DocumentCRUD`: Document 관련 데이터베이스 작업
- `DocumentChunkCRUD`: DocumentChunk 관련 데이터베이스 작업
- `ProcessingJobCRUD`: ProcessingJob 관련 데이터베이스 작업

### 서비스 (services.py)
- `DocumentService`: 문서 관리 비즈니스 로직
- `DocumentChunkService`: 문서 청크 관리 비즈니스 로직
- `ProcessingJobService`: 처리 작업 관리 비즈니스 로직

### 데이터베이스 (database.py)
- `DatabaseManager`: 데이터베이스 연결 관리
- `get_db_session()`: 세션 생성 헬퍼 함수

## 사용법

### 1. 패키지 설치
```bash
# 의존성 설치
pip install -r shared_document_models/requirements.txt

# 패키지를 Python 경로에 추가 (개발 모드)
export PYTHONPATH="${PYTHONPATH}:/path/to/skon"
```

### 2. 데이터베이스 초기화
```python
from shared_document_models import initialize_database

# 환경변수에서 자동으로 DB 설정 읽기
initialize_database()

# 또는 직접 URL 지정
initialize_database("postgresql://user:pass@localhost:5432/dbname")
```

### 3. 서비스 사용
```python
from shared_document_models import DocumentService, get_db_session

# 세션 생성 및 서비스 초기화
with next(get_db_session()) as db:
    doc_service = DocumentService(db, upload_base_path="/uploads")
    
    # 문서 생성
    result = doc_service.create_document_from_path(
        file_path="/path/to/document.pdf",
        user_id="user123",
        document_type="common"
    )
    
    # 문서 조회
    document = doc_service.get_document(result["document_id"])
```

### 4. CRUD 직접 사용
```python
from shared_document_models import DocumentCRUD, get_db_session

with next(get_db_session()) as db:
    doc_crud = DocumentCRUD(db)
    
    # 문서 생성
    document = doc_crud.create_document(
        document_id="doc_123",
        document_name="test.pdf",
        original_filename="test.pdf",
        file_key="user123/test.pdf",
        file_size=1024,
        file_type="application/pdf",
        file_extension="pdf",
        user_id="user123",
        upload_path="/uploads/user123/test.pdf"
    )
```

## 환경변수

데이터베이스 연결을 위한 환경변수:

```bash
# PostgreSQL 개별 설정
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=document_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# 또는 전체 URL
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

## 마이그레이션

기존 프로젝트에서 이 공통 모듈로 마이그레이션하는 방법:

### Backend 프로젝트
1. 기존 `document_models.py`, `document_crud.py`, `document_service.py` 백업
2. Import 경로 변경:
   ```python
   # 기존
   from ai_backend.database.models.document_models import Document
   from ai_backend.database.crud.document_crud import DocumentCRUD
   
   # 변경 후
   from shared_document_models import Document, DocumentCRUD
   ```

### Prefect 프로젝트
1. 기존 `database.py`의 Document 모델 백업
2. Import 경로 변경:
   ```python
   # 기존
   from database import Document, DocumentChunk
   
   # 변경 후
   from shared_document_models import Document, DocumentChunk
   ```

## 호환성

- Python 3.8+
- SQLAlchemy 1.4+
- PostgreSQL 12+
