# OpenClaw Douyin Skills Pack

这是一套面向 OpenClaw 的抖音工作流 skill 包，基于 TikHub 的接口能力设计。当前包含 5 个 skill：

1. `douyin-subscription-manager`
2. `douyin-video-harvester`
3. `douyin-shot-analysis-kb`
4. `douyin-hot-video-script-generator`
5. `douyin-single-video-fetcher`

## 这次版本的重点升级

这次不是再加一层空描述，而是把 **单视频 skill 升级成一条可落地的数据流水线入口**。

现在单视频流程的目标是：

1. 调 TikHub 拿到单条作品接口返回
2. **原始返回完整保存到本地 JSON**
3. 从返回里抽取有效字段，把 **视频 URL / 音乐 URL / 本地路径 / 分析状态** 写入 MySQL
4. 下载视频和音乐到本地，并按目录分组
5. 下载完成后立刻产出一份 **每视频单独的 MD 分析文档**
6. 后续做知识库或脚本生成时，**优先读本地 MD，而不是重复读原始 JSON**

换句话说，原始 JSON 是证据底稿，MySQL 是索引与调度层，MD 是分析层的主入口。

---

## 推荐目录结构

```text
openclaw-douyin-skills/
  README.md
  db/
    douyin_media_schema.sql
  douyin-subscription-manager/
    SKILL.md
  douyin-video-harvester/
    SKILL.md
  douyin-shot-analysis-kb/
    SKILL.md
    references/
    scripts/
  douyin-hot-video-script-generator/
    SKILL.md
    scripts/
  douyin-single-video-fetcher/
    SKILL.md
    references/
    scripts/
```

运行时建议在你的项目侧准备一个数据根目录，例如：

```text
storage/
  raw_api/
    douyin_single_video/
      2026-03-22/
        1234567890.json
  normalized/
    douyin_single_video/
      1234567890.json
  downloads/
    videos/
      creator-slug/
        1234567890.mp4
    music/
      creator-slug/
        music_987654321.mp3
  analysis_md/
    creator-slug/
      1234567890.md
```

---

## 数据职责怎么分

### 1. 原始 JSON
保存 TikHub 接口完整返回。

用途：
- 审计
- 回放
- 字段补提取
- 排查解析 bug

### 2. MySQL
不存整坨原始 JSON，重点存：
- 视频主键与创作者标识
- 视频 URL / 音乐 URL
- 本地文件路径
- 下载状态
- 分析状态
- 本地 MD 路径

用途：
- 快速查询
- 去重
- 调度下载
- 标记分析是否完成

### 3. 本地 MD
每条视频一份分析文档。

用途：
- 人可读
- 模型可读
- 作为后续知识库和脚本生成的主输入

这一步是关键。以后再分析，不应该每次都从原始 JSON 重新拼接语义，而应该直接读取这份 MD。

---

## 单视频流水线怎么跑

### 输入
你需要至少提供其中一个：
- `aweme_id`
- 抖音单条作品链接
- 含链接的分享文本
- 单条作品 URL

### 输出
单视频 skill 现在应该产出这些东西：

1. `raw_api/douyin_single_video/<date>/<video_id>.json`
2. `normalized/douyin_single_video/<video_id>.json`
3. MySQL 中的：
   - `creators`
   - `videos`
   - `music_assets`
   - `video_music_map`
   - `api_fetch_logs`
4. `downloads/videos/<creator>/<video_id>.<ext>`
5. `downloads/music/<creator>/<music_key>.<ext>`
6. `analysis_md/<creator>/<video_id>.md`

### 核心顺序

1. fetch one video
2. save raw JSON
3. normalize fields
4. upsert MySQL rows
5. download video and music
6. update local paths and statuses
7. generate per-video markdown analysis
8. future downstream reading uses local MD first

---

## 环境变量建议

至少准备这些：

```bash
TIKHUB_API_TOKEN=your_tikhub_token
MYSQL_DSN=mysql://user:password@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4
DOUYIN_STORAGE_ROOT=/absolute/path/to/storage
```

说明：
- `MYSQL_DSN` 给单视频 pipeline 用
- `DOUYIN_STORAGE_ROOT` 用来统一存 raw json / downloads / md

---

## SQL 结构

SQL 已经放在：

```text
db/douyin_media_schema.sql
```

数据库结构的设计原则：
- 原始 JSON 在本地文件，不强塞数据库
- 数据库只存高价值索引字段和状态字段
- 一个视频对应一条 `videos`
- 音乐作为独立 `music_assets`
- 中间关系放在 `video_music_map`
- 接口调用留痕放 `api_fetch_logs`

---

## 技能之间现在的推荐关系

### A. 单视频链路
- `douyin-single-video-fetcher`
- `douyin-shot-analysis-kb`（读取本地 MD 做聚合）
- `douyin-hot-video-script-generator`（读取 MD / KB 生成脚本）

### B. 账号级链路
- `douyin-subscription-manager`
- `douyin-video-harvester`
- `douyin-shot-analysis-kb`
- `douyin-hot-video-script-generator`

---

## 重要边界

### 现在已经做对的部分
- 原始响应本地留痕
- 有效 URL 入库
- 下载和分析状态可追踪
- 每视频一份 MD
- 下游优先读 MD

### 仍然需要你自己的环境补完的部分
- 真正请求 TikHub 的运行器
- MySQL 连接信息
- 视频下载权限与网络环境
- 更强的视频视觉理解模型

别搞错：这个 skill 包已经把数据结构和工作流焊得更实了，但它不是替你托管执行环境。

---

## 最推荐的实际使用方式

### 先测一条视频
1. 用 `douyin-single-video-fetcher` 跑通一条作品
2. 确认生成了 raw json / normalized json / downloads / md
3. 确认 MySQL 的 `videos` 和 `music_assets` 有记录
4. 再开始做多视频聚合和知识库

先跑通一条，比一上来整号全量抓取更靠谱。
