#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

log() { printf '\n[%s] %s\n' "setup" "$1"; }
have_cmd() { command -v "$1" >/dev/null 2>&1; }

usage() {
  cat <<MSG
用法：
  bash install.sh [选项]

选项：
  --python PATH              指定 Python 可执行文件，默认 python3
  --qdrant-mode MODE         server | local | memory，默认 server
  --skip-python-deps         跳过 pip 依赖安装
  --skip-system-deps         跳过 ffmpeg/ffprobe 安装
  --skip-venv                跳过创建 .venv
  --skip-qdrant              跳过 Qdrant 启动/初始化
  -h, --help                 显示帮助

也支持通过环境变量控制：
  PYTHON_BIN, QDRANT_MODE, SKIP_PIP, SKIP_FFMPEG, SKIP_VENV, SKIP_QDRANT,
  QDRANT_CONTAINER_NAME, QDRANT_HTTP_PORT, QDRANT_GRPC_PORT, QDRANT_STORAGE_DIR,
  QDRANT_URL, ENV_FILE, OPENCLAW_WORKSPACE_DATA_ROOT
MSG
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"; shift 2 ;;
    --qdrant-mode)
      QDRANT_MODE="$2"; shift 2 ;;
    --skip-python-deps)
      SKIP_PIP=1; shift ;;
    --skip-system-deps)
      SKIP_FFMPEG=1; shift ;;
    --skip-venv)
      SKIP_VENV=1; shift ;;
    --skip-qdrant)
      SKIP_QDRANT=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "未知参数: $1" >&2
      usage
      exit 2 ;;
  esac
done

require_python310() {
  "$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(f"需要 Python >= 3.10，当前: {sys.version.split()[0]}")
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
    log "跳过系统依赖安装（SKIP_FFMPEG=1）"
    return 0
  fi
  local sudo_cmd=""
  if [[ "$(id -u)" -ne 0 ]] && have_cmd sudo; then
    sudo_cmd="sudo"
  fi
  if have_cmd apt-get; then
    log "通过 apt-get 安装 ffmpeg"
    $sudo_cmd apt-get update
    $sudo_cmd apt-get install -y ffmpeg
  elif have_cmd brew; then
    log "通过 Homebrew 安装 ffmpeg"
    brew install ffmpeg
  else
    log "未找到 apt-get/brew，无法自动安装 ffmpeg，请手动安装 ffmpeg 和 ffprobe。"
    return 1
  fi
}

ensure_qdrant() {
  local mode="${QDRANT_MODE,,}"
  if [[ "$SKIP_QDRANT" == "1" ]]; then
    log "跳过 Qdrant 初始化（SKIP_QDRANT=1）"
    return 0
  fi
  case "$mode" in
    memory)
      log "Qdrant mode=memory：不启动外部服务"
      upsert_env HAYSTACK_QDRANT_MODE memory
      ;;
    local)
      log "Qdrant mode=local：使用本地持久化目录"
      mkdir -p "$DATA_ROOT/qdrant_local"
      upsert_env HAYSTACK_QDRANT_MODE local
      upsert_env HAYSTACK_QDRANT_PATH "$DATA_ROOT/qdrant_local"
      ;;
    server)
      if ! have_cmd docker; then
        log "未发现 Docker。请安装 Docker，或改用 QDRANT_MODE=local。"
        return 1
      fi
      mkdir -p "$QDRANT_STORAGE_DIR"
      if docker ps --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
        log "Qdrant 容器已在运行: ${QDRANT_CONTAINER_NAME}"
      elif docker ps -a --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
        log "启动现有 Qdrant 容器: ${QDRANT_CONTAINER_NAME}"
        docker start "$QDRANT_CONTAINER_NAME" >/dev/null
      else
        log "拉取并启动 Qdrant Docker 容器"
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
      log "检查 Qdrant 健康状态: ${QDRANT_URL}"
      "$PYTHON_BIN" - <<PY
import json, urllib.request
url='${QDRANT_URL}/collections'
with urllib.request.urlopen(url, timeout=15) as resp:
    payload=json.loads(resp.read().decode('utf-8'))
print(json.dumps({'qdrant_ok': True, 'url': url, 'status': payload.get('status')}, ensure_ascii=False))
PY
      ;;
    *)
      echo "不支持的 QDRANT_MODE: $mode" >&2
      return 1
      ;;
  esac
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
    log "创建虚拟环境: ${VENV_DIR}"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    # shellcheck disable=SC1090
    source "${VENV_DIR}/bin/activate"
  fi
  if [[ "$SKIP_PIP" != "1" ]]; then
    log "安装 Python 依赖"
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
  require_python310
  ensure_env_file
  ensure_data_dirs
  install_python_env
  install_ffmpeg || true
  ensure_qdrant || true
  log "核心命令检查"
  python --version
  if have_cmd ffmpeg; then ffmpeg -version | head -n 1; else echo "ffmpeg: missing"; fi
  if have_cmd ffprobe; then ffprobe -version | head -n 1; else echo "ffprobe: missing"; fi
  cat <<MSG

安装完成。

下一步：
1. 按需编辑 env 文件：
   ${ENV_FILE}

2. 常用配置：
   TIKHUB_API_TOKEN=your_tikhub_token
   MYSQL_DSN=mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4
   QDRANT_URL=${QDRANT_URL}
   OPENCLAW_API_BASE=http://127.0.0.1:11434/v1
   OPENCLAW_MODEL=your-chat-model
   OPENCLAW_EMBEDDING_MODEL=your-embedding-model

3. MySQL schema 仍然手动导入：
   mysql -h 127.0.0.1 -u <user> -p <database> < "${ROOT_DIR}/db/douyin_media_schema.sql"

4. 包体校验：
   python "${ROOT_DIR}/scripts/validate_package.py"

MSG
}

main "$@"
