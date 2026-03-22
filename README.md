# OpenClaw Douyin Skills Pack

这是一套面向 OpenClaw 的抖音工作流 skill 包，基于 TikHub 的接口能力设计。当前包含 5 个 skill：

1. `douyin-subscription-manager`
2. `douyin-video-harvester`
3. `douyin-shot-analysis-kb`
4. `douyin-hot-video-script-generator`
5. `douyin-single-video-fetcher`

## 这次版本的关键调整

这次把“数据根目录由项目侧自由配置”这件事收掉了，原因很直接：那样会让路径约定漂移，README 讲一套，脚本跑一套，后面一更新又会乱。

现在改成 **skill pack 内置数据根目录**：

- 数据统一写在 `openclaw-douyin-skills/data/` 下
- 每个博主固定一个子目录：`data/creators/<creator-slug>/`
- 所有单视频原始 JSON、标准化 JSON、下载资源、分析 MD 都归在这个博主子目录里
- MySQL 只存高价值索引字段，不存整坨原始响应

这个设计更适合你现在的目标，因为它把“抓取、下载、分析、复用”四层固定成了一致的本地协议。

OpenClaw 官方文档说明，skill 本质上就是一个包含 `SKILL.md` 的文件夹，并且可以附带 supporting files；同时 OpenClaw 还明确支持在 skill 指令里用 `{baseDir}` 引用 skill 文件夹路径。([docs.openclaw.ai](https://docs.openclaw.ai/skills))
这意味着把本地数据目录封装在 skill pack 的固定相对路径里，是符合它的技能组织方式的。([docs.openclaw.ai](https://docs.openclaw.ai/skills) , [docs.openclaw.ai](https://docs.openclaw.ai/tools/creating-skills))

## 为什么不再用自由配置的数据根目录

原因有三个。

第一，**路径不稳定**。一旦靠 `DOUYIN_STORAGE_ROOT` 这种外部变量决定目录，开发机、测试机、线上机三边会天然分叉。之后一写脚本，大家都得重新猜路径。

第二，**skill 的复用价值会下降**。OpenClaw 现在的技能加载逻辑就是按技能目录来组织和发现，workspace skill、managed skill、bundled skill 都是围绕 skill folder 工作的。([docs.openclaw.ai](https://docs.openclaw.ai/skills))
既然 skill 本身就是一个目录，把数据协议也固定在 skill pack 里，比把数据扔到外面更一致。

第三，**你当前的需求是“每个博主一个子目录”**。这天然更适合 `data/creators/<creator-slug>/...` 这种封装式结构，而不是一个大而散的自由存储根。

## 现在的固定目录结构

```text
openclaw-douyin-skills/
  README.md
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
  douyin-video-harvester/
    SKILL.md
  douyin-shot-analysis-kb/
    references/
    scripts/
    SKILL.md
  douyin-hot-video-script-generator/
    scripts/
    SKILL.md
  douyin-single-video-fetcher/
    references/
    scripts/
    SKILL.md
  requirements.txt
  install.sh
```

### 每个博主一个子目录，具体是什么意思

例如你抓取 `techoldman` 这个博主，skill 会把它 slug 化成 `techoldman`，然后所有和这个博主有关的数据都写到：

```text
data/creators/techoldman/
```

在这个子目录下面继续分层：

- `raw_api/` 保存 TikHub 原始返回
- `normalized/` 保存标准化后的机器记录
- `downloads/videos/` 保存视频文件
- `downloads/music/` 保存音乐文件
- `analysis_md/` 保存每条视频一份分析文档

这个结构的意义不是“看上去整齐”，而是：

- 以后增量抓取不会和别的博主混在一起
- 你删一个博主的数据时可以整目录处理
- 知识库构建和脚本生成时可以天然按博主维度读取
- 后续做多博主横向比较时也更容易

## 单视频流水线现在怎么落地

### 输入
你至少提供以下之一：

- `aweme_id`
- 抖音单条作品链接
- 含链接的分享文本
- 单条作品 URL

### 输出
单视频 skill 现在会产出这些东西：

1. `data/creators/<creator-slug>/raw_api/douyin_single_video/<date>/<video_id>.json`
2. `data/creators/<creator-slug>/normalized/douyin_single_video/<video_id>.json`
3. MySQL 中的：
   - `creators`
   - `videos`
   - `music_assets`
   - `video_music_map`
   - `api_fetch_logs`
4. `data/creators/<creator-slug>/downloads/videos/<video_id>.<ext>`
5. `data/creators/<creator-slug>/downloads/music/<music-key>.<ext>`
6. `data/creators/<creator-slug>/analysis_md/<video_id>.md`

### 核心顺序

1. fetch one video
2. save raw JSON into creator subtree
3. normalize fields
4. upsert MySQL rows
5. download grouped video and music assets
6. update local paths and statuses
7. generate per-video markdown analysis
8. future downstream reading uses local MD first

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

以后再分析，不应该每次都从原始 JSON 重新拼语义，而应该优先读这份 MD。

## 依赖

### 必要依赖
这些不装，单视频入库流水线就跑不起来：

- Python 3.10+
- MySQL 8.0+ 或兼容版本
- `pymysql`
- `requests`
- `ffmpeg`
- `ffprobe`

作用分别是：
- `pymysql`：把有效字段写入 MySQL
- `requests`：请求和下载资源
- `ffmpeg` / `ffprobe`：提取媒体信息、生成基础分析素材

### 推荐依赖
这些不是硬性要求，但装上后更顺手：

- `python-dotenv`
- `opencv-python`
- `librosa`

说明：
- `opencv-python`：后续做镜头切换、画面变化频率分析
- `librosa`：后续做音乐节奏、BPM、踩点分析

## 一键安装

根目录有：

```text
install.sh
requirements.txt
```

安装方式：

```bash
bash ./install.sh
```

OpenClaw 的脚本约定里也明确说，`scripts/` 目录适合放这类本地工作流辅助脚本，并且脚本应该聚焦、可文档化。([docs.openclaw.ai](https://docs.openclaw.ai/help/scripts))

这个安装脚本会：

1. 创建 `.venv`
2. 安装 `requirements.txt`
3. 检查并尽量安装 `ffmpeg` / `ffprobe`
4. 输出数据库初始化命令和单视频测试命令

如果你不想自动安装 ffmpeg，可以这样：

```bash
SKIP_FFMPEG=1 bash ./install.sh
```

如果你已经有自己的虚拟环境：

```bash
SKIP_VENV=1 bash ./install.sh
```

## 数据库初始化

SQL 文件在：

```text
db/douyin_media_schema.sql
```

初始化示例：

```bash
mysql -h 127.0.0.1 -u <user> -p <database> < ./db/douyin_media_schema.sql
```

## 环境变量

现在只保留两个必要环境变量：

```bash
export TIKHUB_API_TOKEN='your_tikhub_token'
export MYSQL_DSN='mysql://user:pass@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4'
```

不再需要：

```bash
DOUYIN_STORAGE_ROOT
```

因为存储根目录已经被封装在 skill pack 的相对路径中。

## 最小安装后检查

装完后至少确认这几件事：

```bash
python --version
ffmpeg -version
ffprobe -version
```

## 为什么这个版本不会前后矛盾

这次我把约束收紧了：

- 存储根目录不再外置配置
- 单视频流程统一落到 `data/creators/<creator-slug>/`
- README、脚本默认值、skill 说明、安装脚本四处都对齐
- 后续分析统一“先读 MD，再回溯 JSON”

也就是说，这次不是“README 说建议这样，脚本其实还能随便那样”，而是把路径协议真正写死了。

## 一个必须知道的代价

把数据封装进 skill pack 内部，确实更稳，但代价也要说清楚：

- 如果你以后直接覆盖整个 skill pack 目录升级，`data/` 也要注意保留
- 如果你把 skill 当成只读发布物，运行期写入会和“纯静态 skill bundle”概念冲突

不过对你现在这种本地 OpenClaw 工作流场景，这个代价是可接受的。OpenClaw 自身也把 workspace skill 当成本地目录来加载，而不是只读镜像。([docs.openclaw.ai](https://docs.openclaw.ai/skills))

你真正要避免的不是“写进 skill 目录”，而是**升级时把 `data/` 一把删了**。
