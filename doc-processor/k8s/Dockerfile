# Prefect Python 애플리케이션을 위한 Dockerfile
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 헬스체크 엔드포인트 추가
RUN echo 'import requests; print("Health check endpoint ready")' > /app/health_check.py

# 포트 노출
EXPOSE 8000

# 기본 명령어 (컨테이너 실행 시 오버라이드 가능)
CMD ["python", "-c", "print('Prefect Python app container ready')"] 