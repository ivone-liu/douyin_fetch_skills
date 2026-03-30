# 如何使用抖音 Skills v3.1

这份文档只讲怎么用，不重复讲项目背景。环境变量的完整说明和安装参数说明，请优先看根目录 `README.md`。

## 一、先装依赖

推荐先执行：

```bash
bash install.sh --qdrant-mode server
```

然后激活虚拟环境：

```bash
source .venv/bin/activate
```

如果你不想启动 Qdrant 服务端，只想用本地落盘模式：

```bash
bash install.sh --qdrant-mode local
```

如果你只是本地快速验证：

```bash
bash install.sh --qdrant-mode memory --skip-system-deps
```

## 二、常见入口

- `dy-flow`：不知道先做什么时先走它
- `dy-ingest`：接入单条视频
- `dy-subscribe`：订阅/同步博主
- `dy-library`：查看 creators/tasks/artifacts/scripts/renders
- `dy-script`：写脚本、改脚本、按新闻生成脚本包
- `dy-render`：提交渲染、查状态、重试

## 三、直接运行工具

### 1）解析并落地单视频 payload

```bash
python tools/fetch-single-video-payload/scripts/run.py --source "<SOURCE>" --output /tmp/fetched.json
python tools/ingest-video-payload/scripts/run.py --input-json /tmp/fetched.json --source-input "<SOURCE>"
```

### 2）建库与问库

```bash
python tools/build-kb-from-md/scripts/run.py --creator-slug test_creator
python tools/query-kb/scripts/run.py --creator-slug test_creator --query "这个博主的开场钩子有什么规律？" --top-k 5
```

### 3）生成脚本与新闻脚本包

```bash
python tools/generate-script-package/scripts/run.py --kb-json /path/to/knowledge-base.json --request-json /path/to/script_request.json --output /tmp/script.json
python tools/generate-news-video-package/scripts/run.py --request-json /path/to/news_request.json --no-submit
```

### 4）保存脚本版本

```bash
python tools/save-script-version/scripts/run.py --creator-slug test_creator --mode create_from_topic --topic "测试主题" --source-json /tmp/script.json
```

### 5）提交渲染

```bash
python tools/submit-render-task/scripts/run.py --request-json /path/to/render_request.json --download-results
```

## 四、验证

```bash
python scripts/validate_package.py
```

这一步会检查：

- 根目录结构
- `skills/` / `tools/` 完整性
- Python 3.9 语法兼容
- MySQL 5.7 可疑语法
- 本地 RAG 配置解析
- 本地 smoke test
- 是否残留旧目录路径引用

## 五、建议的试跑顺序

建议你第一次跑按这个顺序来：

1. `bash install.sh --qdrant-mode local`
2. `source .venv/bin/activate`
3. `python scripts/validate_package.py`
4. `python tools/fetch-single-video-payload/scripts/run.py ...`
5. `python tools/ingest-video-payload/scripts/run.py ...`
6. `python tools/build-kb-from-md/scripts/run.py ...`
7. `python tools/query-kb/scripts/run.py ...`
8. `python tools/generate-script-package/scripts/run.py ...`

## 六、常见问题

### 1）为什么 install.sh 不再负责 workspace 挂载？

因为 v3.1 开始，`install.sh` 只负责“项目依赖安装与运行初始化”。
这个包本身就是完整项目目录，不再需要通过 `install.sh` 去做 symlink/copy 挂载。

### 2）install.sh 会不会动 MySQL？

不会。
它只准备 Python 依赖、ffmpeg、`.env`、数据目录和 Qdrant。

### 3）为什么现在默认推荐 server 模式？

因为你明确要把 Qdrant 安装进去，而不是只准备一个本地路径。server 模式会直接通过 Docker 拉起本机 Qdrant，更接近真实运行形态。

### 4）什么时候用 local 模式？

当你不想依赖 Docker 服务端，只想让 Haystack 直接使用本地持久化目录时。


## Python 3.9 说明

- 默认只安装 `requirements.txt`，这是 Python 3.9 兼容线。
- 如需本地 sentence-transformers 嵌入，再手动安装 `requirements.optional-local-embeddings.txt`。
- 若使用 OpenClaw / OpenAI 兼容接口做 embedding，可不安装本地 transformers 栈。
