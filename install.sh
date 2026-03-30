#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SKIP_FFMPEG="${SKIP_FFMPEG:-0}"
SKIP_VENV="${SKIP_VENV:-0}"
SKIP_PIP="${SKIP_PIP:-0}"
SKIP_QDRANT="${SKIP_QDRANT:-0}"
QDRANT_CONTAINER_NAME="${QDRANT_CONTAINER_NAME:-douyin-qdrant}"
QDRANT_HTTP_PORT="${QDRANT_HTTP_PORT:-6333}"
QDRANT_GRPC_PORT="${QDRANT_GRPC_PORT:-6334}"
QDRANT_STORAGE_DIR="${QDRANT_STORAGE_DIR:-$HOME/.openclaw/workspace/qdrant_storage}"
QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:${QDRANT_HTTP_PORT}}"

log() {
  printf '\n[%s] %s\n' "setup" "$1"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_ffmpeg() {
  if have_cmd ffmpeg && have_cmd ffprobe; then
    log "ffmpeg / ffprobe already installed"
    return 0
  fi

  if [[ "$SKIP_FFMPEG" == "1" ]]; then
    log "SKIP_FFMPEG=1, skipping ffmpeg installation"
    return 0
  fi

  if have_cmd apt-get; then
    log "Installing ffmpeg via apt-get"
    sudo apt-get update
    sudo apt-get install -y ffmpeg
  elif have_cmd brew; then
    log "Installing ffmpeg via Homebrew"
    brew install ffmpeg
  else
    log "Could not auto-install ffmpeg. Please install ffmpeg and ffprobe manually."
    return 1
  fi
}

ensure_qdrant() {
  if [[ "$SKIP_QDRANT" == "1" ]]; then
    log "SKIP_QDRANT=1, skipping Qdrant docker startup"
    return 0
  fi

  if ! have_cmd docker; then
    log "Docker not found. Install Docker and start local Qdrant manually if you want RAG features."
    return 0
  fi

  mkdir -p "$QDRANT_STORAGE_DIR"

  if docker ps --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
    log "Qdrant container already running: ${QDRANT_CONTAINER_NAME}"
  elif docker ps -a --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
    log "Starting existing Qdrant container: ${QDRANT_CONTAINER_NAME}"
    docker start "$QDRANT_CONTAINER_NAME" >/dev/null
  else
    log "Pulling and starting Qdrant docker container"
    docker pull qdrant/qdrant
    docker run -d \
      --name "$QDRANT_CONTAINER_NAME" \
      -p "${QDRANT_HTTP_PORT}:6333" \
      -p "${QDRANT_GRPC_PORT}:6334" \
      -v "${QDRANT_STORAGE_DIR}:/qdrant/storage:z" \
      qdrant/qdrant >/dev/null
  fi

  log "Checking Qdrant health at ${QDRANT_URL}"
  python - <<PY
import json, urllib.request
url = '${QDRANT_URL}/collections'
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    print(json.dumps({'qdrant_ok': True, 'url': url, 'status': payload.get('status')}, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({'qdrant_ok': False, 'url': url, 'error': str(exc)}, ensure_ascii=False))
PY
}

main() {
  log "Project root: ${ROOT_DIR}"

  if ! have_cmd "$PYTHON_BIN"; then
    echo "Python not found: ${PYTHON_BIN}" >&2
    exit 1
  fi

  if [[ "$SKIP_VENV" != "1" ]]; then
    log "Creating virtual environment at ${VENV_DIR}"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    # shellcheck disable=SC1090
    source "${VENV_DIR}/bin/activate"
  fi

  if [[ "$SKIP_PIP" != "1" ]]; then
    log "Installing Python dependencies"
    python -m pip install --upgrade pip
    python -m pip install -r "${ROOT_DIR}/requirements.txt"
  fi

  install_ffmpeg || true
  ensure_qdrant || true

  log "Validating core commands"
  python --version
  if have_cmd ffmpeg; then ffmpeg -version | head -n 1; else echo "ffmpeg: missing"; fi
  if have_cmd ffprobe; then ffprobe -version | head -n 1; else echo "ffprobe: missing"; fi

  cat <<MSG

Install complete.

Next steps:
1. Set environment variables:
   export TIKHUB_API_TOKEN='your_tikhub_token'
   export MYSQL_DSN='mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4'
   export QDRANT_URL='${QDRANT_URL}'

2. Optional if you want Haystack to use your OpenClaw-compatible embedding/LLM endpoint instead of local sentence-transformers:
   export OPENAI_API_KEY='your_openclaw_or_openai_key'
   export OPENAI_API_BASE='your_openclaw_compatible_base_url'
   export OPENAI_MODEL='your_openclaw_chat_model'
   export OPENAI_EMBEDDING_MODEL='your_openclaw_embedding_model'

3. Initialize MySQL schema:
   mysql -h 127.0.0.1 -u <user> -p <database> < "${ROOT_DIR}/db/douyin_media_schema.sql"

4. Build a Haystack + Qdrant KB from analysis markdown:
   python "${ROOT_DIR}/douyin-shot-analysis-kb/scripts/build_kb_from_md.py" \
     ~/.openclaw/workspace/data/creators/<creator-slug>/analysis_md

5. Query the KB:
   python "${ROOT_DIR}/douyin-shot-analysis-kb/scripts/query_kb.py" \
     ~/.openclaw/workspace/data/creators/<creator-slug>/kb/knowledge-base.json \
     "这个账号最常见的开头钩子是什么？"

6. Generate a script from the RAG KB:
   python "${ROOT_DIR}/douyin-hot-video-script-generator/scripts/generate_script.py" \
     ~/.openclaw/workspace/data/creators/<creator-slug>/kb/knowledge-base.json \
     /path/to/request.json

MSG
}

main "$@"
