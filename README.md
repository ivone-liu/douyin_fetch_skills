# OpenClaw Douyin Skills Pack

这是一套面向 OpenClaw 的抖音工作流 skill 包，基于 TikHub 提供的数据能力设计。**当前已升级为 4 个 skill**：

1. `douyin-subscription-manager`
2. `douyin-video-harvester`
3. `douyin-shot-analysis-kb`
4. `douyin-hot-video-script-generator`

这 4 个 skill 现在形成一条完整链路：

- **订阅管理**：维护长期跟踪的抖音账号名单
- **视频抓取**：把指定账号的全部短视频尽量完整抓下来
- **知识库构建与查询**：将视频数据与分析结果沉淀为结构化知识库，并可复用、可查询
- **脚本生成**：根据用户真实目标，读取知识库并生成一条更接近“热门视频”的脚本草案

## 这次升级后最大的变化

原来的 `douyin-shot-analysis-kb` 只有“分析说明书 + 脚手架脚本”，只能产出一个 markdown 初稿，**不能算完整知识库**。

现在它已经升级为：

- 能定义知识库存储结构
- 能把分析结果沉淀到 `kb/` 目录
- 能区分原始数据、逐条分析、模式规则、可读总结
- 能被后续脚本生成 skill 读取和复用

换句话说，原来是“分析文档模板”，现在才更接近“可持续更新的知识资产”。

---

## 当前状态

这套 skill **已经适合作为可加载的 skill 规范包使用**，但它仍不是“零配置即可直接联网抓抖音并自动产出爆款脚本”的成品插件。

它现在包含的是：

- skill 的职责定义
- 调用时机说明
- 输入输出约定
- 工作流拆分
- 本地知识库存储规范
- 部分可执行脚本样例

它**还不包含**一套完全焊死的 TikHub 执行器和视频视觉理解流水线。也就是说：

- Skill 负责告诉模型“什么时候用哪把刀”
- 真实请求 TikHub 的逻辑，需要由你的 OpenClaw 运行环境或后续脚本执行
- 视频镜头分析的深水区，仍需要你接入可播放视频、OCR、ASR、视频理解模型或人工校验

## 目录结构

```text
openclaw-douyin-skills/
  README.md
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
    references/
    scripts/
```

## 推荐使用顺序

1. 用 `douyin-subscription-manager` 维护你要长期跟踪的账号
2. 用 `douyin-video-harvester` 把目标账号的历史视频抓全
3. 用 `douyin-shot-analysis-kb` 沉淀为知识库
4. 用 `douyin-hot-video-script-generator` 结合知识库与用户目标生成脚本

这 4 步里，**第 3 步是关键分水岭**。如果第 3 步只是写一篇泛泛的总结，你后面的脚本生成就会变成空转。只有当知识库是结构化、可追溯、可更新的，第 4 步才有意义。

## 订阅后的抓取模式

这次又补了一层关键策略：**订阅**和**抓取策略**分开，但在注册表里强绑定。

用户在订阅账号后，可以选择两种模式：

- `backfill_all`：首次订阅后，回补该账号全部历史视频，再进入后续增量同步
- `latest_only`：从订阅当下开始跟踪，只抓订阅之后发布的新视频，不回补历史

### 为什么这样设计

TikHub 文档目前能明确确认两件事：
- 抖音主页作品接口支持 `max_cursor` 分页，第一页从 `0` 开始，后续使用上一次响应中的 `max_cursor` 继续翻页。
- 作品列表接口支持 `sort_type`，其中 `0` 是**最新排序**，`1` 是**最热排序**。

这足够我们自己实现“全量回补”与“从现在开始增量追踪”两种模式。

但我没有在 TikHub 文档中找到“订阅后自动推送新增视频”“Webhook 回调”“创作者发新视频订阅通知”这类原生能力。因此，`latest_only` 不能依赖 TikHub 自动推送，只能由本地 registry 记录一个**订阅基线时间**，后续通过轮询主页作品接口并按发布时间过滤来实现。

### 当前最终实现策略

- 如果用户选择 `backfill_all`：
  - 订阅注册后立即执行全量抓取
  - 抓取完成后记录 `last_synced_at` 和 `latest_seen_create_time`
- 如果用户选择 `latest_only`：
  - 订阅注册时只写入 creator registry，不回补历史
  - 记录 `subscription_started_at` 作为增量下界
  - 后续同步时只抓发布时间 >= `subscription_started_at` 的作品

### 本地注册表新增字段

每个订阅对象建议额外保存：

- `subscription_mode`: `backfill_all` | `latest_only`
- `subscription_started_at`: 用户开始订阅的时间
- `backfill_completed_at`: 仅全量回补成功后写入
- `latest_seen_create_time`: 最近一次同步中见到的最新作品发布时间
- `last_sync_cursor`: 可选，保留最近一次翻页状态
- `last_synced_at`: 最近一次同步完成时间

### 默认策略

若用户没有明确说明，默认使用 `backfill_all`。因为这更稳，也更符合“先建完整知识库再分析”的需求。只有当用户明确说“不要补历史，只跟踪今后的新内容”时，才使用 `latest_only`。

## TikHub Key 放哪里

不要把 Key 写进 `SKILL.md`、`README.md`、`references/*.md` 或脚本源码。

统一使用环境变量：

```bash
export TIKHUB_API_TOKEN="你的_tikhub_token"
```

或写到 `.env`：

```env
TIKHUB_API_TOKEN=你的_tikhub_token
```

推荐额外支持：

```env
TIKHUB_BASE_URL=https://api.tikhub.io
```

## 知识库现在如何管理

推荐目录：

```text
data/
  raw/
    creator-slug/
  normalized/
    creator-slug/
  analysis/
    creator-slug/
      video-analysis.jsonl
  kb/
    creator-slug/
      knowledge-base.json
      knowledge-base.md
      patterns.json
      sample-index.json
```

### 各层含义

- `raw/`：TikHub 原始返回
- `normalized/`：抓取后清洗统一的视频字段
- `analysis/`：逐条视频分析结果
- `kb/`：模式归纳、总结、可读知识库

## 现在知识库到底具备什么能力

### 具备的
- 规范知识库目录结构
- 输出结构化 JSON 知识库
- 输出 Markdown 总结
- 记录样本来源和证据视频 id
- 允许后续 skill 查询和复用

### 还不具备的
- 自动观看全部视频并精准识别镜头语言
- 自动完成高质量 OCR / ASR / 视频理解
- 自动保证“热门脚本”一定爆

最后这一条尤其要清醒。知识库能提高命中率，但不能替你越过内容质量、选题、时机、账号权重这些现实变量。
