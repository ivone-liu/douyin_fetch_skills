# review v3.1

本轮 review 额外覆盖：

- `install.sh` 改为“项目依赖安装与初始化”，不再负责 skill 挂载
- Python >= 3.9 检查
- `.venv` 初始化逻辑检查
- `ffmpeg / ffprobe` 依赖检查
- `~/.openclaw/.env` 初始化与关键字段写回检查
- Qdrant `local / memory / server` 三种模式初始化检查
- `bash -n install.sh` 语法检查
- 包内静态校验与本地 smoke test
