# 抖音 Skills v3.3

这是一个面向 **OpenClaw / AgentSkills 兼容宿主** 的抖音内容工作流技能包。它把 **视频接入、博主订阅、资源查询、风格分析、知识库构建与检索、脚本生成、审核、视频渲染** 拆成了清晰阶段，并提供根技能与子技能两种入口。

这份 README 重点讲三件事：

1. 这个项目是什么
2. 整个项目的依赖如何安装
3. `~/.openclaw/.env` 应该怎么配

更细的操作步骤请看根目录 `how_to_use.md`。

---

## 一、这是什么

这套包适合以下场景：

- 解析单条抖音视频并落地到本地资产库
- 通过单条视频反查博主并建立订阅/同步
- 对本地视频做结构化风格分析
- 用 **Haystack + 本地/本机 Qdrant** 构建或查询风格知识库
- 使用 **OpenClaw 提供的 OpenAI 兼容基座模型** 做 RAG 问答、脚本生成、脚本改写
- 提交火山引擎视频生成任务并管理结果

---

## 二、目录说明

- `SKILL.md`：根技能，兼容只识别根目录技能的宿主
- `README.md`：给人看的总览、依赖安装、配置说明
- `how_to_use.md`：给人看的操作手册，侧重流程与示例
- `Project.md`：设计文档、边界与数据流说明
- `skills/`：面向用户或流程调度的技能入口
- `tools/`：确定性 Python 工具层
- `scripts/`：当前版本的原生实现脚本目录，包含接入、分析、建库、检索、脚本生成、新闻脚本包生成等实现
- `common/`：共享运行时库
- `db/`：MySQL schema（只提供 SQL，不由安装脚本执行）
- `docs/`：架构与 review 文档
- `references/`：给 AI 读取的参考资料

---

## 三、安装方式

### 1）推荐方式

直接在项目根目录执行：

```bash
bash install.sh
```

这个脚本现在做的是“**整个项目依赖安装与初始化**”，不是 skill 挂载器。它会：

- 检查 Python 是否 >= 3.10
- 创建 `.venv`
- 安装 `requirements.txt`
- 检查并尽量安装 `ffmpeg / ffprobe`
- 准备 `~/.openclaw/.env`
- 准备本地数据目录
- 根据配置初始化 Qdrant（`local` / `memory` / `server`）

### 2）常见参数

```bash
bash install.sh --help
```

常用示例：

#### 本地落盘 Qdrant（推荐开发用）

```bash
QDRANT_MODE=local bash install.sh
```

#### 内存模式（只适合测试）

```bash
QDRANT_MODE=server bash install.sh
```

#### 本机 Docker 启动 Qdrant 服务端

```bash
QDRANT_MODE=memory bash install.sh
```

#### 跳过 Python 依赖安装，只初始化目录和配置

```bash
bash install.sh --skip-python-deps
```

#### 跳过系统依赖安装

```bash
bash install.sh --skip-system-deps
```

---

## 四、运行环境

- Python >= 3.10
- MySQL 5.7+（可选，用于媒体与任务落库）
- Haystack + Qdrant（推荐本地模式）
- OpenClaw 的 OpenAI 兼容模型端点，或标准 OpenAI 兼容端点
- TikHub（可选，用于远程抓取）
- 火山引擎 Ark（可选，用于视频生成）

### 关于 MySQL

安装脚本 **不会**：

- 创建数据库
- 删除表
- 覆盖表结构
- 执行 `db/*.sql`

数据库由你自己控制。

---

### 4）为什么 v3.3 直接要求 Python 3.10+

这版切到了 Haystack / Qdrant 的主线版本，不再维持 Python 3.9 的冻结兼容线。

- Haystack 从 2.22.0 开始要求 Python 3.10+
- qdrant-haystack 当前主线也要求 Python 3.10+
- qdrant-client 当前主线同样要求 Python 3.10+

如果你坚持 Python 3.9，就不能使用这份 v3.3 包。

## 五、`~/.openclaw/.env` 完整配置说明

推荐把下面这些配置写到 `~/.openclaw/.env`。如果你有多个独立 workspace，也可以放在当前项目的 `.env`。

### 1）最小可用配置

如果你只想先跑“本地 RAG + 脚本生成”，最小配置通常是：

```dotenv
OPENCLAW_WORKSPACE_DATA_ROOT=~/.openclaw/workspace/data
HAYSTACK_QDRANT_MODE=local
HAYSTACK_QDRANT_PATH=~/.openclaw/workspace/data/qdrant_local
HAYSTACK_EMBEDDER_BACKEND=openai
OPENCLAW_API_BASE=http://127.0.0.1:11434/v1
OPENCLAW_MODEL=your-chat-model
OPENCLAW_EMBEDDING_MODEL=your-embedding-model
```

### 2）完整配置项

#### A. 数据根目录与本地资产

| 配置项 | 是否必需 | 作用 | 推荐值/说明 |
|---|---:|---|---|
| `OPENCLAW_WORKSPACE_DATA_ROOT` | 强烈推荐 | 所有本地数据、registry、脚本、渲染结果的根目录 | `~/.openclaw/workspace/data` |
| `OPENCLAW_DATA_ROOT` | 可选 | `OPENCLAW_WORKSPACE_DATA_ROOT` 的兼容别名 | 一般不需要同时设置 |
| `MYSQL_DSN` | 可选 | MySQL 媒体索引与任务落库 | `mysql://user:pass@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4` |

#### B. Qdrant / Haystack 向量库

| 配置项 | 是否必需 | 作用 | 推荐值/说明 |
|---|---:|---|---|
| `HAYSTACK_QDRANT_MODE` | 推荐 | Qdrant 运行模式 | `server`、`local`、`memory` |
| `HAYSTACK_QDRANT_PATH` | `local` 模式必需 | Qdrant Local 落盘目录 | `~/.openclaw/workspace/data/qdrant_local` |
| `QDRANT_URL` | `server` 模式必需 | Qdrant 服务端地址 | `http://127.0.0.1:6333` |
| `QDRANT_API_KEY` | 可选 | 远程/鉴权 Qdrant 时使用 | 本地通常留空 |
| `HAYSTACK_QDRANT_COLLECTION_PREFIX` | 可选 | collection 前缀 | 默认 `douyin_creator` |

#### C. Embedding 与生成模型

这里支持两套命名：

- **OpenClaw 兼容命名**：`OPENCLAW_*`
- **标准 OpenAI 兼容命名**：`OPENAI_*`

如果两套都填，代码会优先读取 `OPENAI_*`，再回落到 `OPENCLAW_*`。你最好固定只用一套，别混着配。

| 配置项 | 是否必需 | 作用 | 推荐值/说明 |
|---|---:|---|---|
| `HAYSTACK_EMBEDDER_BACKEND` | 推荐 | Embedding 后端 | `openai` 或 `sentence_transformers` |
| `HAYSTACK_EMBEDDING_MODEL` | `sentence_transformers` 推荐 | 本地嵌入模型名 | 默认 `BAAI/bge-small-zh-v1.5` |
| `OPENCLAW_API_BASE` | OpenClaw 路线推荐 | OpenAI 兼容推理端点 | 例如 `http://127.0.0.1:11434/v1` |
| `OPENCLAW_API_KEY` | 视你的网关而定 | OpenAI 兼容接口的 key | 本地无鉴权可不填 |
| `OPENCLAW_MODEL` | 推荐 | 聊天/生成模型名 | 例如你的本地 chat model |
| `OPENCLAW_EMBEDDING_MODEL` | `openai` backend 推荐 | embedding 模型名 | 例如你的本地 embedding model |
| `OPENAI_API_BASE` | 可选 | 标准 OpenAI 兼容 base URL | 与 OpenClaw 二选一 |
| `OPENAI_API_KEY` | 可选 | 标准 OpenAI 兼容 key | 与 OpenClaw 二选一 |
| `OPENAI_MODEL` | 可选 | 标准 OpenAI 兼容聊天模型名 | 与 OpenClaw 二选一 |
| `OPENAI_EMBEDDING_MODEL` | 可选 | 标准 OpenAI 兼容 embedding 模型名 | 与 OpenClaw 二选一 |
| `OPENAI_BASE_URL` | 可选 | `OPENAI_API_BASE` 兼容别名 | 不推荐与前者同时混用 |
| `MODEL` | 可选 | LLM 模型最终回退值 | 不推荐单独依赖它 |

#### D. TikHub 抓取

| 配置项 | 是否必需 | 作用 | 推荐值/说明 |
|---|---:|---|---|
| `TIKHUB_API_TOKEN` | 用到抓取时必需 | TikHub Bearer Token | 你的 TikHub token |
| `TIKHUB_BASE_URL` | 可选 | TikHub API 根地址 | 默认 `https://api.tikhub.io` |

#### E. 火山引擎视频生成

| 配置项 | 是否必需 | 作用 | 推荐值/说明 |
|---|---:|---|---|
| `ARK_API_KEY` | 推荐 | Ark API Key 主字段 | 你的火山引擎 key |
| `VOLCENGINE_ARK_API_KEY` | 可选 | `ARK_API_KEY` 兼容别名 | 二选一即可 |
| `VOLCENGINE_ARK_BASE_URL` | 可选 | Ark Base URL | 默认 `https://ark.cn-beijing.volces.com/api/v3` |
| `ARK_BASE_URL` | 可选 | `VOLCENGINE_ARK_BASE_URL` 兼容别名 | 二选一即可 |
| `VOLCENGINE_VIDEO_MODEL` | 可选 | 图生视频模型名 | 默认 `doubao-seedance-1-5-pro-251215` |
| `ARK_MODEL` | 可选 | `VOLCENGINE_VIDEO_MODEL` 兼容别名 | 二选一即可 |
| `VOLCENGINE_VIDEO_DURATION_SECONDS` | 可选 | 生成时长上限 | 默认 `5` |
| `ARK_MAX_DURATION_SECONDS` | 可选 | 时长兼容别名 | 二选一即可 |

---

## 六、推荐安装组合

### 方案 1：最稳的本地开发组合

- `HAYSTACK_QDRANT_MODE=local`
- `HAYSTACK_EMBEDDER_BACKEND=openai`
- `OPENCLAW_API_BASE` 指向你的 OpenClaw 基座模型
- TikHub / 火山引擎先不配

安装：

```bash
QDRANT_MODE=local bash install.sh
```

### 方案 2：本机 Docker Qdrant 服务端

- `HAYSTACK_QDRANT_MODE=server`
- `QDRANT_URL=http://127.0.0.1:6333`

安装：

```bash
QDRANT_MODE=memory bash install.sh
```

### 方案 3：只跑测试

```bash
QDRANT_MODE=server bash install.sh --skip-system-deps
```

---

## 七、安装完成后下一步做什么

1. 激活虚拟环境

```bash
source .venv/bin/activate
```

2. 校验包本身

```bash
python scripts/validate_package.py
```

3. 继续看 `how_to_use.md`

里面有：

- ingest 示例
- build-kb 示例
- query-kb 示例
- script package 生成示例
- render 示例

---

## 八、先看哪里

- `how_to_use.md`：具体操作流程与命令示例
- `Project.md`：设计说明与数据流
- `docs/review-v3.3.md`：本轮 review 结果
