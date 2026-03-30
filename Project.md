# 抖音 Skills v3.1 项目设计说明

## 目标

这套包的目标不是“兼容旧代码”，而是提供一套 **直接可用、结构单一、无 legacy 依赖** 的抖音工作流技能包。

目标包括：

1. 根目录 `SKILL.md` 可被只识别根技能的宿主读取
2. `skills/` 子技能可被 OpenClaw workspace 模式读取
3. `tools/` 负责确定性执行，不把执行动作混进 prompt
4. `common/` 提供统一共享运行时
5. `scripts/` 保留当前 v3 的原生核心实现
6. 本地 RAG 以 **Haystack + Qdrant** 为核心
7. 安装脚本 `install.sh` 只负责“项目依赖安装与初始化”，不再负责 skill 挂载

## 设计层次

### 1. 根技能

根目录 `SKILL.md` 负责：

- 兼容只识别根 skill 的宿主
- 提供总控入口说明
- 把用户引导到 `dy-flow`、`dy-ingest`、`dy-script`、`dy-render`

### 2. skills/

面向用户的技能入口：

- `dy-flow`
- `dy-ingest`
- `dy-subscribe`
- `dy-library`
- `dy-script`
- `dy-render`
- `dy-video-analysis`
- `dy-kb`
- `dy-review`

### 3. tools/

确定性动作工具层：

- 接入单视频 payload
- 解析/标准化
- 本地视频分析
- 构建知识库
- 查询知识库
- 保存脚本版本
- 提交渲染

### 4. common/

共享基础设施：

- 存储路径
- JSON 工具
- Haystack + Qdrant 封装
- 视频分析底层函数
- 任务状态管理

### 5. scripts/

当前 v3 版本的原生核心实现：

- `pipeline_ingest_single_video.py`
- `analyze_local_video.py`
- `build_kb_from_md.py`
- `query_kb.py`
- `generate_script.py`
- `generate_news_video.py`

## 安装与运行原则

### install.sh 的职责

从 v3.1 开始，`install.sh` 只负责：

- Python 版本检查
- 虚拟环境创建
- Python 依赖安装
- ffmpeg/ffprobe 安装检查
- `.env` 初始化
- 数据目录初始化
- Qdrant 初始化（`local` / `memory` / `server`）

### install.sh 不负责

- skill 挂载
- symlink/copy 到别的 workspace
- 创建 MySQL 数据库
- 执行 `db/*.sql`

## 本地 RAG 设计

### 支持模式

- `memory`：临时测试
- `local`：本地落盘，不依赖 Qdrant 常驻服务
- `server`：本机 Docker 或已有服务端

### 推荐默认值

开发默认推荐：

- `HAYSTACK_QDRANT_MODE=local`
- `HAYSTACK_QDRANT_PATH=~/.openclaw/workspace/data/qdrant_local`

## 为什么不再保留 legacy_runtime

因为 v3 已经把仍在运行的旧版关键实现迁到当前目录：

- 新工具直接调用当前目录 `scripts/`
- 公共模块统一到当前目录 `common/`
- 不再依赖旧目录布局

这保证了目录更干净，也避免了重名模块和 import 阴影。

## 运行数据根目录

默认数据根目录：

```text
~/.openclaw/workspace/data/
```

会用于存放：

- creators
- downloads
- renders
- scripts
- task_registry
- qdrant_local / qdrant_storage

## 结论

v3.1 的关键取舍是：

- 不再把安装脚本当成 skill 挂载器
- 直接把项目目录当作可运行工程
- 把 Qdrant、Haystack、模型配置、ffmpeg 初始化收进安装流程
- 数据库 schema 只提供，不自动执行


## Python 3.9 说明

- 默认只安装 `requirements.txt`，这是 Python 3.9 兼容线。
- 如需本地 sentence-transformers 嵌入，再手动安装 `requirements.optional-local-embeddings.txt`。
- 若使用 OpenClaw / OpenAI 兼容接口做 embedding，可不安装本地 transformers 栈。
