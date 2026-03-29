# OpenClaw Douyin Skills Pack

这是一套面向 **OpenClaw** 的抖音工作流 skill 包，围绕 **TikHub** 提供的数据接口设计。它的目标不是只拿到一份接口返回，而是把“抓取、保存、下载、分析、复用”做成一条能持续运行的本地流水线。

这套项目适合做四类事情：

- 订阅抖音账号，并记录订阅方式与同步策略
- 抓取单条视频或整号视频
- 下载视频和音乐素材，并生成本地分析文档
- 基于本地分析文档构建知识库，再生成热门视频脚本

## 项目包含的 skill

当前包含 6 个 skill：

1. `douyin-subscription-manager`
2. `douyin-video-harvester`
3. `douyin-shot-analysis-kb`
4. `douyin-hot-video-script-generator`
5. `douyin-single-video-fetcher`
6. `douyin-news-video-director`

这 6 个 skill 不是并列重复关系，而是一条链路上的不同环节。

## 这套项目解决什么问题

只调用 TikHub 的单个接口，通常只能拿到“元数据”或者“作品详情”。这不够。你真正需要的是：

- 原始响应留痕，方便回查和补解析
- 高价值字段进入数据库，方便索引、状态管理、去重和调度
- 下载的视频和音乐按博主分组保存，避免后续混乱
- 每条视频生成一份本地 Markdown 分析文档，并在文档内嵌入结构化 JSON 分析块，作为后续知识库和脚本生成的主要输入

所以这套项目采用的是下面这条固定链路：

**TikHub 接口返回 → 本地原始 JSON → 标准化 JSON → MySQL 索引 → 本地下载 → 每条视频一份 Markdown → 基于 Markdown 做知识库和脚本生成**

## 目录结构

项目目录结构如下：

```text
openclaw-douyin-skills/
  README.md
  requirements.txt
  install.sh
  db/
    douyin_media_schema.sql
  data/
    creators/
      <creator-slug>/
        raw_api/
          douyin_single_video/
            <yyyy-mm-dd>/
              <aweme_id>.json
        normalized/
          douyin_single_video/
            <aweme_id>.json
        downloads/
          videos/
            <aweme_id>.<ext>
          music/
            <music-key>.<ext>
        analysis_md/
          <aweme_id>.md
  douyin-subscription-manager/
    SKILL.md
    references/
  douyin-video-harvester/
    SKILL.md
    references/
    scripts/
  douyin-shot-analysis-kb/
    SKILL.md
    references/
    scripts/
  douyin-hot-video-script-generator/
    SKILL.md
    references/
    scripts/
  douyin-single-video-fetcher/
    SKILL.md
    references/
    scripts/
```

## 数据存在哪里

这套项目的数据根目录固定在 OpenClaw workspace 下，不依赖 repo 内部目录。

所有本地数据都放在：

```text
~/.openclaw/workspace/data/
```

其中每个博主一个子目录：

```text
~/.openclaw/workspace/data/creators/<creator-slug>/
```

这个约定是项目的一部分，不需要你再单独配置一个 `DOUYIN_STORAGE_ROOT`。这样做的目的很直接：

- 一个博主的数据不会和另一个博主混在一起
- 迁移、备份、删除某个博主的数据更容易
- 后续知识库和脚本生成天然按博主维度处理
- 项目在不同机器上更稳定，不容易出现“文档说一套、实际路径又是另一套”

### 每个博主目录下的数据分层

#### 1. `raw_api/`
保存 TikHub 原始响应。

示例：

```text
~/.openclaw/workspace/data/creators/techoldman/raw_api/douyin_single_video/2026-03-22/7448118827402972455.json
```

用途：

- 审计
- 回放
- 字段补提取
- 排查解析问题

#### 2. `normalized/`
保存标准化后的结构化 JSON。

示例：

```text
~/.openclaw/workspace/data/creators/techoldman/normalized/douyin_single_video/7448118827402972455.json
```

用途：

- 统一字段命名
- 减少后续脚本重复解析原始响应
- 为数据库写入和后续分析提供稳定结构

#### 3. `downloads/videos/`
保存视频文件。

示例：

```text
~/.openclaw/workspace/data/creators/techoldman/downloads/videos/7448118827402972455.mp4
```

#### 4. `downloads/music/`
保存音乐文件。

示例：

```text
~/.openclaw/workspace/data/creators/techoldman/downloads/music/1234567890.mp3
```

#### 5. `analysis_md/`
每条视频生成一份 Markdown 分析文档。文档内包含人可读说明和一个结构化 JSON 分析块。

示例：

```text
~/.openclaw/workspace/data/creators/techoldman/analysis_md/7448118827402972455.md
```

用途：

- 人可读
- 模型可读
- 作为知识库构建和脚本生成的主输入

后续如果要做内容分析、知识库总结、脚本生成，**优先读本地 MD，不优先读原始 JSON**。

## MySQL 里存什么

MySQL 只保存高价值索引字段和状态信息，不保存整坨原始接口响应。

这样设计的原因是：

- 原始响应应该保留在本地文件中，方便完整追溯
- 数据库更适合存索引、路径、状态、去重字段和关系映射

数据库建表文件在：

```text
db/douyin_media_schema.sql
```

包含这些表：

### `creators`
保存博主信息。

主要字段包括：

- `sec_user_id`
- `unique_id`
- `display_name`
- `avatar_url`
- `signature`

### `videos`
保存视频主记录。

主要字段包括：

- `aweme_id`
- `creator_id`
- `desc_text`
- `create_time`
- `duration_ms`
- `play_url`
- `raw_json_path`
- `normalized_json_path`
- `local_video_path`
- `local_analysis_md_path`
- `download_status`
- `analysis_status`

### `music_assets`
保存音乐素材信息。

主要字段包括：

- `music_id`
- `title`
- `author_name`
- `play_url`
- `local_music_path`
- `download_status`

### `video_music_map`
保存视频和音乐的关系映射。

### `api_fetch_logs`
保存接口抓取日志。

主要用于记录：

- 来源类型
- 来源输入
- 接口名
- 请求参数
- 响应码
- 原始 JSON 路径
- 关联 `aweme_id`

## 运行依赖

### 必要依赖

这些不装，项目跑不起来：

- Python 3.10+
- MySQL 8.0+ 或兼容版本
- `pymysql`
- `requests`
- `ffmpeg`
- `ffprobe`

它们分别负责：

- `pymysql`：写入和更新 MySQL
- `requests`：调用接口、下载资源
- `ffmpeg` / `ffprobe`：读取媒体信息、提取基础音视频信息、为分析准备素材

### 推荐依赖

这些不是最低运行要求，但建议安装：

- `python-dotenv`
- `opencv-python`
- `librosa`

它们分别用于：

- `python-dotenv`：更方便管理环境变量
- `opencv-python`：后续扩展镜头切换、画面变化频率分析
- `librosa`：后续扩展音乐节奏、BPM、踩点分析

## 安装

### 1. 解压项目

把 zip 解压到本地目录，例如：

```bash
unzip openclaw-douyin-skills-v7.zip
cd openclaw-douyin-skills
```

### 2. 一键安装依赖

项目根目录提供了一键安装脚本：

```bash
bash ./install.sh
```

这个脚本会：

- 创建 `.venv`
- 安装 `requirements.txt`
- 尝试自动安装 `ffmpeg`
- 输出数据库初始化命令
- 输出单视频测试命令

#### 可选参数

跳过自动安装 ffmpeg：

```bash
SKIP_FFMPEG=1 bash ./install.sh
```

跳过创建虚拟环境：

```bash
SKIP_VENV=1 bash ./install.sh
```

跳过 Python 依赖安装：

```bash
SKIP_PIP=1 bash ./install.sh
```

### 3. 设置环境变量

至少需要两个环境变量：

```bash
export TIKHUB_API_TOKEN='your_tikhub_token'
export MYSQL_DSN='mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4'
```

说明：

- `TIKHUB_API_TOKEN` 用于访问 TikHub API
- `MYSQL_DSN` 用于连接 MySQL

### 4. 初始化数据库

执行：

```bash
mysql -h 127.0.0.1 -u <user> -p <database> < ./db/douyin_media_schema.sql
```

注意，这个 SQL 文件内部已经包含：

```sql
CREATE DATABASE IF NOT EXISTS openclaw_douyin;
USE openclaw_douyin;
```

所以实际执行时，你也可以直接：

```bash
mysql -h 127.0.0.1 -u <user> -p < ./db/douyin_media_schema.sql
```

## 在 OpenClaw 中安装 skill

如果你要把这套项目接到 OpenClaw 使用，推荐把整个项目放到 OpenClaw 的 skill 目录中。

常见方式：

### 方式一：当前 workspace 专用

```text
<workspace>/skills/openclaw-douyin-skills/
```

### 方式二：当前用户全局可用

```text
~/.openclaw/skills/openclaw-douyin-skills/
```

然后在 OpenClaw 配置中给相关 skill 注入环境变量，例如：

```json
{
  "skills": {
    "entries": {
      "douyin-single-video-fetcher": {
        "enabled": true,
        "env": {
          "TIKHUB_API_TOKEN": "your_tikhub_token",
          "MYSQL_DSN": "mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4"
        }
      },
      "douyin-video-harvester": {
        "enabled": true,
        "env": {
          "TIKHUB_API_TOKEN": "your_tikhub_token",
          "MYSQL_DSN": "mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4"
        }
      },
      "douyin-shot-analysis-kb": {
        "enabled": true,
        "env": {
          "TIKHUB_API_TOKEN": "your_tikhub_token",
          "MYSQL_DSN": "mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4"
        }
      },
      "douyin-hot-video-script-generator": {
        "enabled": true
      },
      "douyin-subscription-manager": {
        "enabled": true,
        "env": {
          "TIKHUB_API_TOKEN": "your_tikhub_token",
          "MYSQL_DSN": "mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4"
        }
      }
    }
  }
}
```

## 每个 skill 是什么，怎么用

### 1. `douyin-single-video-fetcher`

用途：

- 获取一条抖音视频
- 保存 TikHub 原始响应到本地 JSON
- 提取高价值字段写入 MySQL
- 下载视频和音乐到本地
- 下载完成后立即生成一份本地 Markdown 分析文档

适合场景：

- 只看一条视频
- 测试单条作品流水线是否正常
- 想快速落一条视频的本地记录

输入优先级：

1. `aweme_id`
2. 单条视频分享链接
3. 含链接的分享文本
4. 单条视频 URL

#### 推荐脚本

主入口脚本：

```text
douyin-single-video-fetcher/scripts/pipeline_ingest_single_video.py
```

辅助脚本：

```text
douyin-single-video-fetcher/scripts/fetch_single_video.py
douyin-single-video-fetcher/scripts/read_local_md.py
```

#### 最小测试

你已经拿到 TikHub 的单视频原始 JSON 时，可以先测单条流水线：

```bash
python ./douyin-single-video-fetcher/scripts/pipeline_ingest_single_video.py \
  /path/to/raw_payload.json \
  --mysql-dsn "$MYSQL_DSN" \
  --endpoint-name fetch_one_video_v2 \
  --source-input 'https://v.douyin.com/xxxx/'
```

这条命令会做这些事：

- 从原始 JSON 解析核心字段
- 创建博主目录
- 保存标准化 JSON
- 更新 MySQL
- 下载视频和音乐
- 生成对应的 Markdown 分析文档

### 2. `douyin-video-harvester`

用途：

- 抓取一个抖音账号的作品列表
- 支持全量历史抓取
- 支持从订阅开始时间起做增量抓取
- 作为整号级别的数据入口

适合场景：

- 需要一个博主的全部视频
- 需要从订阅开始持续跟踪新增作品

典型模式：

- `backfill_all`：补抓历史视频
- `latest_only`：从当前开始只追踪新增视频

它和 `douyin-single-video-fetcher` 的区别很直接：

- `douyin-single-video-fetcher` 只负责一条视频
- `douyin-video-harvester` 负责一个账号的作品集合

### 3. `douyin-subscription-manager`

用途：

- 管理抖音账号订阅记录
- 记录订阅模式
- 记录订阅起始时间
- 为后续同步提供状态基础

适合场景：

- 你想“先订阅，再同步”
- 你需要区分“历史回补”和“只看新增”

它管理的是“追踪关系”，不是下载本身。

### 4. `douyin-shot-analysis-kb`

用途：

- 读取本地 Markdown 分析文档
- 汇总一个博主的多条视频分析结果
- 生成知识库 JSON 和 Markdown
- 为后续脚本生成提供可复用模式

它不是直接读 TikHub 原始响应来做知识库，而是**优先读取本地 `analysis_md/`**。

#### 主要脚本

```text
douyin-shot-analysis-kb/scripts/build_kb.py
douyin-shot-analysis-kb/scripts/build_kb_from_md.py
douyin-shot-analysis-kb/scripts/query_kb.py
```

#### 典型用法

从某个博主的 MD 目录构建知识库：

```bash
python ./douyin-shot-analysis-kb/scripts/build_kb_from_md.py \
  ./~/.openclaw/workspace/data/creators/techoldman/analysis_md \
  ./~/.openclaw/workspace/data/creators/techoldman/kb
```

输出一般包括：

- `knowledge-base.json`
- `knowledge-base.md`

### 5. `douyin-hot-video-script-generator`

用途：

- 读取知识库
- 结合用户主题、目标受众、目标动作
- 生成一版短视频脚本草案

它不直接抓 TikHub 数据，而是使用前面已经沉淀下来的知识库。

#### 主要脚本

```text
douyin-hot-video-script-generator/scripts/generate_script.py
```

#### 典型用法

先准备一个请求文件 `request.json`：

```json
{
  "topic": "产品经理如何开始做副业",
  "audience": "上班族",
  "goal": "提高完播和互动"
}
```

再执行：

```bash
python ./douyin-hot-video-script-generator/scripts/generate_script.py \
  ./~/.openclaw/workspace/data/creators/techoldman/kb/knowledge-base.json \
  ./request.json
```


### 6. `douyin-news-video-director`

用途：

- 读取一个或多个已有知识库
- 围绕外部新闻生成新的短视频角度
- 产出完整脚本、分镜和模型提示词
- 调用火山引擎视频生成接口并下载结果到本地

主要脚本：

```text
douyin-news-video-director/scripts/generate_news_video.py
```

输出目录默认位于：

```text
~/.openclaw/workspace/data/creators/<creator-slug>/generated_scripts/news_video/
~/.openclaw/workspace/data/creators/<creator-slug>/generated_videos/news_video/
```

## 推荐工作流

### 工作流 A：先跑单条视频

适合先验证整个项目能不能跑通。

1. 准备一条单视频的 TikHub 原始 JSON
2. 运行 `pipeline_ingest_single_video.py`
3. 检查本地目录是否生成：
   - raw JSON
   - normalized JSON
   - 下载的视频
   - 下载的音乐
   - Markdown 分析文档
4. 检查 MySQL 中相关表是否有记录

### 工作流 B：订阅博主并持续追踪

1. 用 `douyin-subscription-manager` 建立订阅关系
2. 选择订阅模式：
   - `backfill_all`
   - `latest_only`
3. 用 `douyin-video-harvester` 抓取作品列表
4. 对每条视频继续走单视频入库流水线
5. 周期性同步新作品

### 工作流 C：构建知识库并生成脚本

1. 确保某个博主已经有足够多的 `analysis_md/*.md`
2. 用 `douyin-shot-analysis-kb` 构建知识库
3. 用 `douyin-hot-video-script-generator` 基于知识库生成脚本

## 项目当前的真实能力边界

这部分我直接说清楚，避免你误判。

### 现在已经能做的

- 保存 TikHub 原始响应
- 本地保存原始 JSON 和标准化 JSON
- 把视频 URL、音乐 URL、路径和状态写入 MySQL
- 按博主分组保存视频和音乐文件
- 为每条视频生成一个本地 Markdown 分析文档
- 读取本地 Markdown 构建知识库
- 基于知识库生成脚本草案

### 现在不能装作已经做完的

- 不能仅凭 TikHub 元数据就准确识别全部运镜
- 不能只靠文案就得出可靠的视觉拍摄结论
- 不能保证“生成的脚本一定爆”

你要做真正的拍摄方法、镜头语言、节奏踩点分析，还要继续扩展：

- `opencv-python`
- `librosa`
- 音频转写
- 视觉模型或多模态模型

目前这套项目已经把“数据链路”和“存储协议”搭好了，后续增强分析能力只是在这条链上继续加能力，而不是推翻重来。

## 常见问题

### 为什么本地还要保存原始 JSON？

因为数据库不是证据仓库。数据库只存高价值字段和状态，原始 JSON 才是完整留痕。

### 为什么后续分析优先读 Markdown，而不是直接读原始 JSON？

因为原始 JSON 更适合回查和补解析，不适合每次都重新做语义层分析。Markdown 是为“反复阅读和下游复用”准备的。

### 为什么每个博主一个目录？

因为这是最稳的组织方式。否则多个博主混在一起，后面清理、增量抓取、知识库构建都会越来越乱。

### 为什么音乐和视频要同时存本地和数据库？

- 本地存文件，是为了真正拥有素材
- 数据库存 URL 和本地路径，是为了检索、状态管理和后续调度

## 下一步建议

最务实的做法是：

1. 先跑通单条视频流水线
2. 再接整号抓取
3. 再构建知识库
4. 最后再做脚本生成和更深的镜头分析

不要一开始就把所有增强分析都堆进来。先让这条链稳定，再谈更复杂的视觉和音乐理解。


## Ark 图生视频最小配置

`douyin-news-video-director` 现在按你给的 Ark 图生视频接口固定实现，不再要求一长串视频生成环境变量。

放在 `~/.openclaw/.env` 里的最小配置只有：

```bash
OPENCLAW_WORKSPACE_DATA_ROOT=~/.openclaw/workspace/data
ARK_API_KEY=你的_ARK_API_KEY
```

说明：

- `ARK_API_KEY` 是唯一必需的火山引擎配置。
- 代码里已经固定：
  - 提交接口：`https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`
  - 查询接口：`https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}`
  - 请求方法：`POST`
  - 查询方法：`GET`
  - 模型：`doubao-seedance-1-5-pro-251215`
  - 默认时长：`5` 秒
- 之前那些 `VOLCENGINE_VIDEO_*` 环境变量，当前这版不再需要你手工配置。

图生视频仍然需要在请求里提供可访问的 `reference_image_url`。这是业务输入，不是环境变量。
