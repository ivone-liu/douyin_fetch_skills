#!/usr/bin/env bash
set -euo pipefail

PKG_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="python3"
VENV_DIR="$PKG_ROOT/.venv"
ENV_PATH=""
DATA_ROOT=""
QDRANT_MODE=""
START_QDRANT="auto"   # auto|docker|skip
SYSTEM_DEPS="auto"    # auto|skip
PYTHON_DEPS="install" # install|skip
QDRANT_CONTAINER="douyin-skills-qdrant"
QDRANT_PORT="6333"
QDRANT_GRPC_PORT="6334"

usage() {
  cat <<USAGE
用法：
  bash install.sh [选项]

说明：
  这个脚本负责“整个项目运行依赖”的安装与初始化，不再负责 skill 挂载。
  它会：
  1. 检查 Python >= 3.9
  2. 创建本地虚拟环境 .venv
  3. 安装 requirements.txt 中的 Python 依赖
  4. 尝试安装系统依赖 ffmpeg/ffprobe（可跳过）
  5. 准备 ~/.openclaw/.env（或你指定的 env 文件）
  6. 准备本地数据目录
  7. 按配置初始化 Qdrant：local / memory / server

注意：
  - 不会创建、覆盖、删除你的 MySQL 数据库或表
  - 不会执行 db/*.sql
  - 如果你选择 Qdrant server 模式，默认通过 Docker 启动本地容器

选项：
  --python <path>              指定 Python，可执行文件默认 python3
  --venv <path>                指定虚拟环境目录，默认 ./.venv
  --env-file <path>            指定配置文件；默认优先读取当前目录 .env，其次 ~/.openclaw/.env
  --data-root <path>           指定数据根目录；默认来自 env 或 ~/.openclaw/workspace/data
  --qdrant-mode <mode>         local | memory | server，默认读取 env，未配置时默认 local
  --start-qdrant <mode>        auto | docker | skip，默认 auto
  --container-name <name>      Qdrant Docker 容器名，默认 douyin-skills-qdrant
  --qdrant-port <port>         Qdrant REST 端口，默认 6333
  --qdrant-grpc-port <port>    Qdrant gRPC 端口，默认 6334
  --skip-python-deps           跳过 pip 安装，仅做目录/配置准备
  --skip-system-deps           跳过 ffmpeg/ffprobe 检查与安装
  --help                       查看帮助
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python) PYTHON_BIN="$2"; shift 2 ;;
    --venv) VENV_DIR="$2"; shift 2 ;;
    --env-file) ENV_PATH="$2"; shift 2 ;;
    --data-root) DATA_ROOT="$2"; shift 2 ;;
    --qdrant-mode) QDRANT_MODE="$2"; shift 2 ;;
    --start-qdrant) START_QDRANT="$2"; shift 2 ;;
    --container-name) QDRANT_CONTAINER="$2"; shift 2 ;;
    --qdrant-port) QDRANT_PORT="$2"; shift 2 ;;
    --qdrant-grpc-port) QDRANT_GRPC_PORT="$2"; shift 2 ;;
    --skip-python-deps) PYTHON_DEPS="skip"; shift ;;
    --skip-system-deps) SYSTEM_DEPS="skip"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "未知参数: $1" >&2; usage; exit 2 ;;
  esac
done

log() { echo "[install] $*"; }
err() { echo "[install][ERROR] $*" >&2; }

ensure_python_version() {
  "$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit(f"需要 Python >= 3.9，当前是 {sys.version.split()[0]}")
PY
}

expand_path() {
  "$PYTHON_BIN" - <<'PY' "$1"
import os, sys
print(os.path.abspath(os.path.expandvars(os.path.expanduser(sys.argv[1]))))
PY
}

ensure_env_file() {
  mkdir -p "$HOME/.openclaw"
  if [[ -n "$ENV_PATH" ]]; then
    ENV_PATH="$(expand_path "$ENV_PATH")"
  elif [[ -f "$PKG_ROOT/.env" ]]; then
    ENV_PATH="$PKG_ROOT/.env"
  elif [[ -f "$HOME/.openclaw/.env" ]]; then
    ENV_PATH="$HOME/.openclaw/.env"
  else
    ENV_PATH="$HOME/.openclaw/.env"
    cp "$PKG_ROOT/.env.example" "$ENV_PATH"
    log "未发现现成 env，已从 .env.example 初始化到: $ENV_PATH"
  fi
}

load_env_file() {
  if [[ -f "$ENV_PATH" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_PATH"
    set +a
  fi
}

upsert_env() {
  local key="$1"
  local value="$2"
  [[ -n "$ENV_PATH" ]] || return 0
  mkdir -p "$(dirname "$ENV_PATH")"
  touch "$ENV_PATH"
  if grep -Eq "^[# ]*${key}=" "$ENV_PATH"; then
    "$PYTHON_BIN" - <<'PY' "$ENV_PATH" "$key" "$value"
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
    printf '%s=%s\n' "$key" "$value" >> "$ENV_PATH"
  fi
}

ensure_system_dep_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
    log "已检测到 ffmpeg / ffprobe"
    return 0
  fi
  if [[ "$SYSTEM_DEPS" == "skip" ]]; then
    err "未检测到 ffmpeg / ffprobe，但你选择了 --skip-system-deps。视频分析相关能力可能不可用。"
    return 0
  fi

  local sudo_cmd=""
  if [[ "$(id -u)" -ne 0 ]] && command -v sudo >/dev/null 2>&1; then
    sudo_cmd="sudo"
  fi

  if command -v apt-get >/dev/null 2>&1; then
    log "尝试通过 apt-get 安装 ffmpeg"
    $sudo_cmd apt-get update
    $sudo_cmd apt-get install -y ffmpeg
  elif command -v brew >/dev/null 2>&1; then
    log "尝试通过 Homebrew 安装 ffmpeg"
    brew install ffmpeg
  else
    err "未检测到 apt-get 或 brew，无法自动安装 ffmpeg。请手动安装后重试。"
    return 1
  fi

  command -v ffmpeg >/dev/null 2>&1 || { err "ffmpeg 安装失败"; return 1; }
  command -v ffprobe >/dev/null 2>&1 || { err "ffprobe 安装失败"; return 1; }
  log "ffmpeg / ffprobe 安装完成"
}

ensure_python_env() {
  VENV_DIR="$(expand_path "$VENV_DIR")"
  if [[ ! -d "$VENV_DIR" ]]; then
    log "创建虚拟环境: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  if [[ "$PYTHON_DEPS" == "skip" ]]; then
    log "跳过 Python 依赖安装"
    return 0
  fi
  log "安装 Python 依赖"
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install -r "$PKG_ROOT/requirements.txt"
}

prepare_data_dirs() {
  local default_root="${OPENCLAW_WORKSPACE_DATA_ROOT:-${OPENCLAW_DATA_ROOT:-$HOME/.openclaw/workspace/data}}"
  if [[ -z "$DATA_ROOT" ]]; then
    DATA_ROOT="$default_root"
  fi
  DATA_ROOT="$(expand_path "$DATA_ROOT")"
  mkdir -p \
    "$DATA_ROOT" \
    "$DATA_ROOT/creators" \
    "$DATA_ROOT/downloads" \
    "$DATA_ROOT/renders" \
    "$DATA_ROOT/scripts" \
    "$DATA_ROOT/task_registry" \
    "$DATA_ROOT/tmp"
  upsert_env OPENCLAW_WORKSPACE_DATA_ROOT "$DATA_ROOT"
  log "数据根目录: $DATA_ROOT"
}

prepare_qdrant() {
  local env_mode="${HAYSTACK_QDRANT_MODE:-local}"
  local mode="${QDRANT_MODE:-$env_mode}"
  mode="${mode,,}"
  case "$mode" in
    local|memory|server) ;;
    *) err "不支持的 Qdrant 模式: $mode"; return 1 ;;
  esac

  upsert_env HAYSTACK_QDRANT_MODE "$mode"

  if [[ "$mode" == "memory" ]]; then
    log "Qdrant 模式: memory（仅测试用，不会持久化）"
    return 0
  fi

  if [[ "$mode" == "local" ]]; then
    local qdrant_path="${HAYSTACK_QDRANT_PATH:-$DATA_ROOT/qdrant_local}"
    qdrant_path="$(expand_path "$qdrant_path")"
    mkdir -p "$qdrant_path"
    upsert_env HAYSTACK_QDRANT_PATH "$qdrant_path"
    log "Qdrant 模式: local，落盘目录: $qdrant_path"
    return 0
  fi

  local qdrant_url="${QDRANT_URL:-http://127.0.0.1:${QDRANT_PORT}}"
  upsert_env QDRANT_URL "$qdrant_url"
  if [[ "$START_QDRANT" == "skip" ]]; then
    log "Qdrant 模式: server，已跳过自动启动。请自行确保服务可用: $qdrant_url"
    return 0
  fi

  if ! command -v docker >/dev/null 2>&1; then
    err "Qdrant server 模式默认通过 Docker 启动，但当前未检测到 docker。"
    err "你可以改用 --qdrant-mode local，或先安装 Docker。"
    return 1
  fi

  local storage_dir="$DATA_ROOT/qdrant_storage"
  mkdir -p "$storage_dir"
  if docker ps --format '{{.Names}}' | grep -Fxq "$QDRANT_CONTAINER"; then
    log "Qdrant 容器已运行: $QDRANT_CONTAINER"
  elif docker ps -a --format '{{.Names}}' | grep -Fxq "$QDRANT_CONTAINER"; then
    log "启动已存在的 Qdrant 容器: $QDRANT_CONTAINER"
    docker start "$QDRANT_CONTAINER" >/dev/null
  else
    log "拉取并启动本地 Qdrant Docker 容器"
    docker pull qdrant/qdrant
    docker run -d \
      --name "$QDRANT_CONTAINER" \
      -p "${QDRANT_PORT}:6333" \
      -p "${QDRANT_GRPC_PORT}:6334" \
      -v "$storage_dir:/qdrant/storage" \
      qdrant/qdrant >/dev/null
  fi
  log "Qdrant 服务地址: $qdrant_url"
}

print_summary() {
  cat <<SUMMARY

安装完成。

已完成：
- Python 运行环境检查
- 虚拟环境准备：$(expand_path "$VENV_DIR")
- Python 依赖安装：$PYTHON_DEPS
- 系统依赖 ffmpeg 处理：$SYSTEM_DEPS
- env 文件：$ENV_PATH
- 数据根目录：$DATA_ROOT
- Qdrant 模式：${QDRANT_MODE:-${HAYSTACK_QDRANT_MODE:-local}}

注意：
- install.sh 不会执行 db/*.sql，也不会覆盖你的 MySQL 数据库。
- 接下来建议执行：
  1. source "$(expand_path "$VENV_DIR")/bin/activate"
  2. python scripts/validate_package.py
  3. 按 README.md / how_to_use.md 跑 ingest、build-kb、query-kb、generate-script
SUMMARY
}

main() {
  ensure_python_version
  ensure_env_file
  load_env_file
  ensure_system_dep_ffmpeg
  ensure_python_env
  prepare_data_dirs
  prepare_qdrant
  print_summary
}

main "$@"


echo "[info] Python 3.9 默认不安装本地 sentence-transformers / transformers 栈。"
echo "[info] 如需本地嵌入，请手动安装 requirements.optional-local-embeddings.txt"
