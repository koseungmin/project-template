# syntax=docker/dockerfile:1.7

# Build and push doc_processor/Dockerfile.base to your internal registry and
# replace the reference below with that image tag.
FROM registry.internal.example.com/base/python-3.12-doc:latest AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PREFECT_HOME=/opt/prefect

WORKDIR /app

# Copy dependency descriptors separately for better layer caching
COPY doc_processor/requirements.txt /tmp/doc_processor_requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/doc_processor_requirements.txt

# Copy shared core libraries and application source
COPY shared_core /app/shared_core
COPY doc_processor /app

RUN chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app:/app/shared_core \
    PREFECT_API_URL=http://127.0.0.1:4200/api \
    PREFECT_UI_URL=http://127.0.0.1:4200 \
    PREFECT_DISABLE_TELEMETRY=1 \
    START_PREFECT_SERVER=1 \
    RUN_PREFECT_DEPLOY=1 \
    START_PREFECT_WORKER=1

EXPOSE 4200

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -fsS http://127.0.0.1:4200/api/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/entrypoint.sh"]

