#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SKIP_FFMPEG="${SKIP_FFMPEG:-0}"
SKIP_VENV="${SKIP_VENV:-0}"
SKIP_PIP="${SKIP_PIP:-0}"

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
   export DOUYIN_STORAGE_ROOT='${ROOT_DIR}/storage'

2. Initialize the database schema:
   mysql -h 127.0.0.1 -u <user> -p <database> < "${ROOT_DIR}/db/douyin_media_schema.sql"

3. Test single-video ingestion:
   python "${ROOT_DIR}/douyin-single-video-fetcher/scripts/pipeline_ingest_single_video.py" \
     /path/to/raw_payload.json \
     --storage-root "${ROOT_DIR}/storage" \
     --mysql-dsn "\$MYSQL_DSN" \
     --endpoint-name fetch_one_video_v2 \
     --source-input 'https://v.douyin.com/xxxx/'

MSG
}

main "$@"
