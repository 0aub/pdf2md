#!/bin/bash
set -euo pipefail

# ============================================================================
# pdf2md — Convert PDF pages to organized Markdown with image descriptions
# ============================================================================
#
# Usage:
#   ./run.sh <pdf_path> <start_page> <end_page> [--title "Book Title"]
#
# Example:
#   ./run.sh "/mnt/d/Books/textbook.pdf" 1 100 --title "My Textbook"
#
# Prerequisites:
#   - Docker with NVIDIA GPU support (nvidia-docker)
#   - NVIDIA GPU with >= 8GB VRAM (recommended: 16GB+)
#   - ~10GB disk space for model cache + page images
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse arguments
PDF_PATH="${1:?Usage: ./run.sh <pdf_path> <start_page> <end_page> [--title 'Title']}"
START_PAGE="${2:?Missing start page}"
END_PAGE="${3:?Missing end page}"
TITLE=""

shift 3
while [[ $# -gt 0 ]]; do
    case "$1" in
        --title) TITLE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

TOTAL_PAGES=$((END_PAGE - START_PAGE + 1))
PAGE_OFFSET=$((START_PAGE - 1))
HF_CACHE="${HOME}/.cache/huggingface"
WORK_DIR="${SCRIPT_DIR}"

echo "============================================"
echo "  pdf2md Pipeline"
echo "============================================"
echo "  PDF:    ${PDF_PATH}"
echo "  Pages:  ${START_PAGE}-${END_PAGE} (${TOTAL_PAGES} pages)"
echo "  Title:  ${TITLE:-'(none)'}"
echo "============================================"
echo ""

mkdir -p "${HF_CACHE}"
mkdir -p "${WORK_DIR}/pages"
mkdir -p "${WORK_DIR}/ocr_results"
mkdir -p "${WORK_DIR}/output"

# ── Step 1: Split PDF ──────────────────────────────────────────────────────
echo "=== Step 1/4: Splitting PDF ==="
docker build -t pdf2md-split -f "${SCRIPT_DIR}/docker/Dockerfile.split" "${SCRIPT_DIR}" 2>/dev/null

if [ -f "${WORK_DIR}/output/subset.pdf" ]; then
    echo "  Subset PDF already exists, skipping."
else
    docker run --rm \
        -v "$(dirname "${PDF_PATH}"):/data:ro" \
        -v "${WORK_DIR}/output:/output" \
        pdf2md-split \
        "/data/$(basename "${PDF_PATH}")" "/output/subset.pdf" "${START_PAGE}" "${END_PAGE}"
fi

# ── Step 2: Extract page images ────────────────────────────────────────────
echo ""
echo "=== Step 2/4: Extracting page images ==="
docker build -t pdf2md-extract -f "${SCRIPT_DIR}/docker/Dockerfile.extract" "${SCRIPT_DIR}" 2>/dev/null

BATCH=50
for ((s=1; s<=TOTAL_PAGES; s+=BATCH)); do
    e=$((s + BATCH - 1))
    [ $e -gt $TOTAL_PAGES ] && e=$TOTAL_PAGES

    last_page=$(printf "${WORK_DIR}/pages/page_%04d.png" $e)
    if [ -f "$last_page" ]; then
        echo "  Pages $s-$e already extracted, skipping."
        continue
    fi

    echo "  Extracting pages $s-$e..."
    docker run --rm \
        -v "${WORK_DIR}/output:/data:ro" \
        -v "${WORK_DIR}/pages:/output/pages" \
        -e PDF_INPUT="/data/subset.pdf" \
        pdf2md-extract $s $e
done

# ── Step 3: Run DeepSeek-OCR ──────────────────────────────────────────────
echo ""
echo "=== Step 3/4: Running DeepSeek-OCR ==="
docker build -t pdf2md-ocr -f "${SCRIPT_DIR}/docker/Dockerfile.ocr" "${SCRIPT_DIR}" 2>/dev/null

docker run --rm --gpus all \
    --init \
    -e PYTHONUNBUFFERED=1 \
    -v "${WORK_DIR}/pages:/data/pages:ro" \
    -v "${WORK_DIR}/ocr_results:/output/ocr_results" \
    -v "${HF_CACHE}:/root/.cache/huggingface" \
    pdf2md-ocr 1 ${TOTAL_PAGES}

# ── Step 4: Clean up and combine ──────────────────────────────────────────
echo ""
echo "=== Step 4/4: Combining into Markdown ==="

TITLE_ARG=""
[ -n "$TITLE" ] && TITLE_ARG="--title \"${TITLE}\""

python3 "${SCRIPT_DIR}/scripts/cleanup_ocr.py" \
    "${WORK_DIR}/ocr_results" \
    "${WORK_DIR}/output/result.md" \
    --page-offset ${PAGE_OFFSET} \
    ${TITLE_ARG}

echo ""
echo "============================================"
echo "  DONE!"
echo "  Output: ${WORK_DIR}/output/result.md"
echo "============================================"
