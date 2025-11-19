#!/usr/bin/env bash
set -euo pipefail

PREFECT_SERVER_HOST="${PREFECT_SERVER_HOST:-0.0.0.0}"
PREFECT_SERVER_PORT="${PREFECT_SERVER_PORT:-4200}"
PREFECT_API_URL="${PREFECT_API_URL:-http://127.0.0.1:${PREFECT_SERVER_PORT}/api}"
PREFECT_UI_URL="${PREFECT_UI_URL:-http://127.0.0.1:${PREFECT_SERVER_PORT}}"
PREFECT_WORK_POOL="${PREFECT_WORK_POOL:-default}"
PREFECT_WORK_QUEUE="${PREFECT_WORK_QUEUE:-default}"
PREFECT_WORKER_NAME="${PREFECT_WORKER_NAME:-doc-processor-worker}"
PREFECT_WORKER_LIMIT="${PREFECT_WORKER_LIMIT:-1}"
PREFECT_PREFETCH_SECONDS="${PREFECT_PREFETCH_SECONDS:-1}"
PREFECT_DEPLOY_ARGS="${PREFECT_DEPLOY_ARGS:---all}"
PREFECT_YAML_PATH="${PREFECT_YAML_PATH:-/app/base/prefect.yaml}"
START_PREFECT_SERVER="${START_PREFECT_SERVER:-1}"
START_PREFECT_WORKER="${START_PREFECT_WORKER:-1}"
RUN_PREFECT_DEPLOY="${RUN_PREFECT_DEPLOY:-1}"
PREFECT_HEALTH_TIMEOUT="${PREFECT_HEALTH_TIMEOUT:-180}"

log() {
  echo "[$(date --iso-8601=seconds)] $*"
}

trap_handler() {
  log "Shutdown signal received. Stopping Prefect processes..."
  if [[ -n "${WORKER_PID:-}" ]] && ps -p "${WORKER_PID}" > /dev/null 2>&1; then
    kill "${WORKER_PID}" || true
  fi
  if [[ -n "${SERVER_PID:-}" ]] && ps -p "${SERVER_PID}" > /dev/null 2>&1; then
    kill "${SERVER_PID}" || true
  fi
  wait -n || true
}

trap trap_handler TERM INT

export PREFECT_API_URL
export PREFECT_UI_URL
export PREFECT_DISABLE_TELEMETRY="${PREFECT_DISABLE_TELEMETRY:-1}"
export PREFECT_LOGGING_LEVEL="${PREFECT_LOGGING_LEVEL:-INFO}"

mkdir -p "${PREFECT_HOME:-/opt/prefect}" /root/.prefect

ensure_work_pool() {
  if [[ -z "${PREFECT_WORK_POOL}" ]]; then
    return
  fi
  if prefect work-pool inspect "${PREFECT_WORK_POOL}" >/dev/null 2>&1; then
    log "Prefect work pool '${PREFECT_WORK_POOL}' already exists."
  else
    log "Creating Prefect work pool '${PREFECT_WORK_POOL}' (type=process)..."
    PREFECT_CREATE_ARGS=(work-pool create "${PREFECT_WORK_POOL}" --type process)
    if [[ "${PREFECT_WORK_QUEUE}" != "" && "${PREFECT_WORK_QUEUE}" != "default" ]]; then
      PREFECT_CREATE_ARGS+=(--default-queue "${PREFECT_WORK_QUEUE}")
    fi
    prefect "${PREFECT_CREATE_ARGS[@]}"
  fi
}

if [[ "${START_PREFECT_SERVER}" == "1" ]]; then
  log "Starting Prefect server on ${PREFECT_SERVER_HOST}:${PREFECT_SERVER_PORT}..."
  prefect server start \
    --host "${PREFECT_SERVER_HOST}" \
    --port "${PREFECT_SERVER_PORT}" &
  SERVER_PID=$!
  log "Prefect server PID: ${SERVER_PID}"
else
  log "Skipping Prefect server start because START_PREFECT_SERVER=${START_PREFECT_SERVER}"
fi

if [[ "${START_PREFECT_SERVER}" == "1" ]]; then
  START_TIME=$(date +%s)
  HEALTH_URL="${PREFECT_API_URL%/}/health"
  log "Waiting for Prefect API at ${HEALTH_URL} (timeout ${PREFECT_HEALTH_TIMEOUT}s)..."
  SERVER_EXIT_LOGGED=0

  until curl -fsS "${HEALTH_URL}" > /dev/null; do
    sleep 3
    if [[ -n "${SERVER_PID:-}" ]] && ! ps -p "${SERVER_PID}" > /dev/null 2>&1; then
      if [[ "${SERVER_EXIT_LOGGED}" -eq 0 ]]; then
        log "Prefect server launcher process exited; continuing to wait for API readiness."
        SERVER_EXIT_LOGGED=1
      fi
    fi
    NOW=$(date +%s)
    if (( NOW - START_TIME > PREFECT_HEALTH_TIMEOUT )); then
      log "Timed out waiting for Prefect server health."
      exit 1
    fi
  done
  log "Prefect API is ready."
fi

if [[ "${RUN_PREFECT_DEPLOY}" == "1" || "${START_PREFECT_WORKER}" == "1" ]]; then
  ensure_work_pool
fi

if [[ "${RUN_PREFECT_DEPLOY}" == "1" ]]; then
  if [[ -f "${PREFECT_YAML_PATH}" ]]; then
    log "Running 'prefect deploy --prefect-file ${PREFECT_YAML_PATH} --all'..."
    # Prefect 3.x에서는 --prefect-file과 --all 옵션 사용, /app 디렉토리에서 실행
    if cd /app && prefect deploy --prefect-file "${PREFECT_YAML_PATH}" --all; then
      log "Prefect deployments registered successfully."
    else
      log "Prefect deployment command failed."
    fi
  else
    log "prefect.yaml not found at ${PREFECT_YAML_PATH}. Skipping deployment."
    log "Set PREFECT_YAML_PATH environment variable to specify custom path."
  fi
else
  log "Skipping Prefect deployment because RUN_PREFECT_DEPLOY=${RUN_PREFECT_DEPLOY}."
fi

if [[ "${START_PREFECT_WORKER}" == "1" ]]; then
  log "Starting Prefect worker '${PREFECT_WORKER_NAME}' (pool=${PREFECT_WORK_POOL}, queue=${PREFECT_WORK_QUEUE})..."
  WORKER_CMD=(
    prefect worker start
    --pool "${PREFECT_WORK_POOL}"
    --name "${PREFECT_WORKER_NAME}"
    --limit "${PREFECT_WORKER_LIMIT}"
    --prefetch-seconds "${PREFECT_PREFETCH_SECONDS}"
  )
  if [[ -n "${PREFECT_WORK_QUEUE}" ]]; then
    WORKER_CMD+=(--work-queue "${PREFECT_WORK_QUEUE}")
  fi
  "${WORKER_CMD[@]}" &
  WORKER_PID=$!
  log "Prefect worker PID: ${WORKER_PID}"
  wait "${WORKER_PID}"
else
  log "Prefect worker disabled (START_PREFECT_WORKER=${START_PREFECT_WORKER}). Container will remain running."
  tail -f /dev/null
fi

