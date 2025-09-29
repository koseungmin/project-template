# 📄 Document Processing Pipeline with Prefect


AI 기반 문서 처리 파이프라인입니다. PDF 문서에서 텍스트와 이미지를 추출하고, GPT Vision으로 이미지 설명을 생성한 후, 벡터 데이터베이스에 저장하여 검색 가능하도록 만드는 완전 자동화된 시스템입니다.

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
cp prefect.yaml.example prefect.yaml
cp k8s/configmap.yaml.example k8s/configmap.yaml
# 각 파일에서 Azure OpenAI 설정 정보 입력
```

### 2. 데이터베이스 설정

```bash
# PostgreSQL 설치 및 설정 (선택사항)
# 자세한 내용은 POSTGRES_SETUP.md 참조
```

### 3. Prefect 서버 및 워커 실행

```bash
# 터미널 1: Prefect 서버 시작
python base/start_prefect_server.py

# 터미널 2: 파이프라인 배포
python base/deploy_pipeline.py

# 터미널 3: 워커 시작
python base/start_worker.py
```

### 4. 파이프라인 실행

**웹 UI에서 실행 (추천):**
1. http://127.0.0.1:4200 접속
2. Deployments → `document-processing-pipeline` 선택
3. Quick Run 클릭하여 실행

**명령줄에서 직접 실행:**
```bash
python run_document_pipeline.py
```

## 📊 파이프라인 구조

```
📦 프로젝트/
├── 🎛️ base/                    # Prefect 관리 스크립트
├── 🧠 flow/                    # 핵심 파이프라인 로직
├── 🚢 k8s/                     # Kubernetes 배포 설정
├── 📋 prefect.yaml.example     # Prefect 설정 템플릿
├── 🔧 requirements.txt         # Python 패키지
└── 🔍 run_search.py           # 검색 스크립트
```

## 🔍 검색 기능

처리 완료된 문서를 검색할 수 있습니다:

```bash
python run_search.py "검색어"
```

## ⚙️ 주요 설정 파일

- `prefect.yaml`: Prefect 파이프라인 설정 (git에 제외됨)
- `k8s/configmap.yaml`: Kubernetes 환경변수 설정 (git에 제외됨)
- `.env`: 로컬 환경변수 (git에 제외됨)

**사용법**: `.example` 파일들을 복사하여 실제 설정값을 입력하세요.

## 🔧 문제 해결

### 서버 재시작
```bash
pkill -f "prefect.*server"
python base/start_prefect_server.py
```

### 설정 확인
```bash
python -c "from flow.config import config; config.validate_config()"
```

## 📚 추가 정보

- **Prefect UI**: http://127.0.0.1:4200
- **PostgreSQL 설정**: `POSTGRES_SETUP.md` 참조
- **Kubernetes 배포**: `k8s/` 폴더 참조

---

🎉 **시작하기**: `python base/start_prefect_server.py`를 실행하고 Prefect UI에서 파이프라인을 관리하세요!