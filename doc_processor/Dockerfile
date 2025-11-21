# syntax=docker/dockerfile:1.7
# Building for Linux platform from macOS
# Base 이미지 사용: python-pymupdf:3.12-slim (모든 Python 패키지와 시스템 의존성 포함)

FROM --platform=linux/amd64 python-pymupdf:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PREFECT_HOME=/opt/prefect

WORKDIR /app

# Copy dependency descriptors separately for better layer caching
COPY doc_processor/requirements-freeze.txt /tmp/doc_processor_requirements.txt

# Install Python dependencies
# base 이미지에 시스템 의존성은 이미 설치되어 있음
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/doc_processor_requirements.txt && \
    rm /tmp/doc_processor_requirements.txt

# Copy shared core libraries and application source
COPY shared_core /app/shared_core
COPY doc_processor /app

RUN chmod +x /app/entrypoint.sh /app/entrypoint.py

ENV PYTHONPATH=/app:/app/shared_core \
    PREFECT_API_URL=http://127.0.0.1:4200/scheduler/api \
    PREFECT_UI_URL=http://127.0.0.1:4200 \
    PREFECT_SERVER_API_BASE_PATH=/scheduler/api \
    PREFECT_DISABLE_TELEMETRY=1 \
    START_PREFECT_SERVER=1 \
    RUN_PREFECT_DEPLOY=1 \
    START_PREFECT_WORKER=1

EXPOSE 4200

# Health check (base 이미지에 curl이 설치되어 있음)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -fsS http://127.0.0.1:4200/scheduler/api/health || exit 1

# tini를 ENTRYPOINT로 설정 (base 이미지에 설치되어 있음)
ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["python3", "/app/entrypoint.py"]

