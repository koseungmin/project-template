# syntax=docker/dockerfile:1.7
# Building for Linux platform from macOS

FROM --platform=linux/amd64 python:3.12-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PREFECT_HOME=/opt/prefect

# Install system dependencies - MINIMAL TEST (all removed for testing)
# RUN apk add --no-cache \
#     bash \
#     curl \
#     tini \
#     build-base \
#     postgresql-dev \
#     poppler-utils \
#     poppler-dev \
#     jpeg-dev \
#     zlib-dev \
#     freetype-dev \
#     lcms2-dev \
#     openjpeg-dev \
#     tiff-dev \
#     tk-dev \
#     tcl-devk

WORKDIR /app

# Copy dependency descriptors separately for better layer caching
COPY doc_processor/requirements-freeze.txt /tmp/doc_processor_requirements.txt

# Install dependencies (excluding pymilvus/milvus-lite which may not be needed)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/doc_processor_requirements.txt

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

# HEALTHCHECK disabled - curl not available without system packages
# HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
#     CMD curl -fsS http://127.0.0.1:4200/scheduler/api/health || exit 1

# ENTRYPOINT without tini - testing minimal setup
CMD ["python3", "/app/entrypoint.py"]

