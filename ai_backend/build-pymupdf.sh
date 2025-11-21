#!/bin/bash
# PyMuPDF Docker 이미지 빌드 스크립트 (Linux 플랫폼)

set -e

echo "🔨 PyMuPDF Docker 이미지 빌드 시작..."
echo "📦 플랫폼: linux/amd64"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📁 빌드 컨텍스트: $PROJECT_ROOT"
echo "📄 Dockerfile: $SCRIPT_DIR/Dockerfile.pymupdf"
echo ""

# 이전에 빌드된 이미지 삭제 (플랫폼 불일치 방지)
echo "🧹 기존 이미지 정리 중..."
docker rmi python-pymupdf:3.12-slim 2>/dev/null || true

# Linux 플랫폼으로 명시적으로 빌드 (캐시 없이)
# 빌드 컨텍스트를 상위 폴더(project-template)로 설정하여 doc_processor/requirements-freeze.txt 접근 가능
echo "🔨 빌드 시작 (캐시 무시)..."
docker build \
    --platform linux/amd64 \
    --no-cache \
    --pull \
    -f "$SCRIPT_DIR/Dockerfile.pymupdf" \
    -t python-pymupdf:3.12-slim \
    "$PROJECT_ROOT"

echo ""
echo "✅ 빌드 완료!"
echo ""
echo "🧪 이미지 테스트:"
echo "   docker run --rm python-pymupdf:3.12-slim python -c \"import fitz; print('PyMuPDF version:', fitz.version)\""
echo ""
echo "📋 이미지 정보 확인:"
echo "   docker images python-pymupdf:3.12-slim"
echo ""

