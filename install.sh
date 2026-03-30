#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_ROOT="$ROOT_DIR"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SKIP_FFMPEG="${SKIP_FFMPEG:-0}"
SKIP_VENV="${SKIP_VENV:-0}"
SKIP_PIP="${SKIP_PIP:-0}"
SKIP_QDRANT="${SKIP_QDRANT:-0}"
QDRANT_MODE="${QDRANT_MODE:-server}"
QDRANT_CONTAINER_NAME="${QDRANT_CONTAINER_NAME:-douyin-qdrant}"
QDRANT_HTTP_PORT="${QDRANT_HTTP_PORT:-6333}"
QDRANT_GRPC_PORT="${QDRANT_GRPC_PORT:-6334}"
QDRANT_STORAGE_DIR="${QDRANT_STORAGE_DIR:-$HOME/.openclaw/workspace/qdrant_storage}"
QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:${QDRANT_HTTP_PORT}}"
ENV_FILE="${ENV_FILE:-$HOME/.openclaw/.env}"
DATA_ROOT="${OPENCLAW_WORKSPACE_DATA_ROOT:-$HOME/.openclaw/workspace/data}"

log() {
  printf '\n[%s] %s\n' "setup" "$1"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

require_python39() {
  "$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit(f"需要 Python >= 3.9，当前: {sys.version.split()[0]}")
PY
}

ensure_env_file() {
  mkdir -p "$(dirname "$ENV_FILE")"
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ROOT_DIR/.env.example" "$ENV_FILE"
    log "已初始化 env 文件: $ENV_FILE"
  fi
}

upsert_env() {
  local key="$1"
  local value="$2"
  touch "$ENV_FILE"
  if grep -Eq "^[# ]*${key}=" "$ENV_FILE"; then
    "$PYTHON_BIN" - <<'PY' "$ENV_FILE" "$key" "$value"
from pathlib import Path
import sys
path=Path(sys.argv[1])
key=sys.argv[2]
value=sys.argv[3]
lines=path.read_text(encoding='utf-8').splitlines()
out=[]
replaced=False
for line in lines:
    stripped=line.lstrip(' #')
    if stripped.startswith(key + '=') and not replaced:
        out.append(f"{key}={value}")
        replaced=True
    else:
        out.append(line)
if not replaced:
    out.append(f"{key}={value}")
path.write_text("\n".join(out)+"\n", encoding='utf-8')
PY
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
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

  local sudo_cmd=""
  if [[ "$(id -u)" -ne 0 ]] && have_cmd sudo; then
    sudo_cmd="sudo"
  fi

  if have_cmd apt-get; then
    log "Installing ffmpeg via apt-get"
    $sudo_cmd apt-get update
    $sudo_cmd apt-get install -y ffmpeg
  elif have_cmd brew; then
    log "Installing ffmpeg via Homebrew"
    brew install ffmpeg
  else
    log "Could not auto-install ffmpeg. Please install ffmpeg and ffprobe manually."
    return 1
  fi
}

ensure_qdrant() {
  local mode="${QDRANT_MODE,,}"

  if [[ "$SKIP_QDRANT" == "1" ]]; then
    log "SKIP_QDRANT=1, skipping Qdrant setup"
    return 0
  fi

  case "$mode" in
    memory)
      log "Qdrant mode=memory: no external installation required"
      upsert_env HAYSTACK_QDRANT_MODE memory
      return 0
      ;;
    local)
      log "Qdrant mode=local: using embedded local persisted storage"
      mkdir -p "$DATA_ROOT/qdrant_local"
      upsert_env HAYSTACK_QDRANT_MODE local
      upsert_env HAYSTACK_QDRANT_PATH "$DATA_ROOT/qdrant_local"
      return 0
      ;;
    server)
      ;;
    *)
      echo "Unsupported QDRANT_MODE: $mode" >&2
      return 1
      ;;
  esac

  if ! have_cmd docker; then
    log "Docker not found. Install Docker and rerun, or set QDRANT_MODE=local"
    return 1
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

  upsert_env HAYSTACK_QDRANT_MODE server
  upsert_env QDRANT_URL "$QDRANT_URL"

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

ensure_data_dirs() {
  mkdir -p \
    "$DATA_ROOT" \
    "$DATA_ROOT/creators" \
    "$DATA_ROOT/downloads" \
    "$DATA_ROOT/renders" \
    "$DATA_ROOT/scripts" \
    "$DATA_ROOT/task_registry" \
    "$DATA_ROOT/tmp"
  upsert_env OPENCLAW_WORKSPACE_DATA_ROOT "$DATA_ROOT"
}

install_python_env() {
  if [[ "$SKIP_VENV" != "1" ]]; then
    log "Creating virtual environment at ${VENV_DIR}"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    # shellcheck disable=SC1090
    source "${VENV_DIR}/bin/activate"
  fi

  if [[ "$SKIP_PIP" != "1" ]]; then
    log "Installing Python dependencies"
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -r "${ROOT_DIR}/requirements.txt"
  fi
}

main() {
  log "Project root: ${ROOT_DIR}"

  if ! have_cmd "$PYTHON_BIN"; then
    echo "Python not found: ${PYTHON_BIN}" >&2
    exit 1
  fi

  require_python39
  ensure_env_file
  ensure_data_dirs
  install_python_env
  install_ffmpeg || true
  ensure_qdrant || true

  log "Validating core commands"
  python --version
  if have_cmd ffmpeg; then ffmpeg -version | head -n 1; else echo "ffmpeg: missing"; fi
  if have_cmd ffprobe; then ffprobe -version | head -n 1; else echo "ffprobe: missing"; fi

  cat <<MSG

Install complete.

Next steps:
1. Edit env file if needed:
   ${ENV_FILE}

2. Optional core variables:
   TIKHUB_API_TOKEN=your_tikhub_token
   MYSQL_DSN=mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4
   QDRANT_URL=${QDRANT_URL}

3. Optional if you want Haystack to use your OpenClaw-compatible embedding/LLM endpoint instead of local sentence-transformers:
   OPENAI_API_KEY=your_openclaw_or_openai_key
   OPENAI_API_BASE=your_openclaw_compatible_base_url
   OPENAI_MODEL=your_openclaw_chat_model
   OPENAI_EMBEDDING_MODEL=your_openclaw_embedding_model

4. MySQL schema is still manual on purpose:
   mysql -h 127.0.0.1 -u <user> -p <database> < "${ROOT_DIR}/db/douyin_media_schema.sql"

5. Validate package:
   python "${ROOT_DIR}/scripts/validate_package.py"

MSG
}

main "$@"
