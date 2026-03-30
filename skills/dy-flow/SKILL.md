---
name: dy-flow
description: 抖音工作流总控入口，用于在视频接入、博主订阅、资源查看、脚本生成、审核和视频渲染之间做下一步判断。适用于用户只给出一个抖音链接、分享文案或模糊目标，不确定应该先分析、先订阅还是先写脚本的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧭", "category": "workflow"}}
---
# dy-flow

当用户输入模糊、下一步不明确时，优先使用这个技能。

## 这个技能做什么

- 判断用户现在到底想做什么
- 在接入、订阅、查询、脚本、渲染、review 之间做路由
- 避免一上来就执行昂贵或不可回滚的动作

## 路由规则

### 情况 1：用户给了单条视频链接或分享文案
执行：

```bash
python tools/fetch-single-video-payload/scripts/run.py --source "<SOURCE>" --output /tmp/douyin_single_video.json
python tools/ingest-video-payload/scripts/run.py --input-json /tmp/douyin_single_video.json --source-input "<SOURCE>" --run-analysis
```

### 情况 2：用户要订阅博主或同步主页作品
执行：

```bash
python tools/fetch-creator-feed/scripts/run.py --profile-url "<PROFILE_URL>" --max-pages 2
```

### 情况 3：用户要查看已经存在的资产、任务或脚本
执行：

```bash
python tools/list-library-entities/scripts/run.py --entity creators
python tools/list-library-entities/scripts/run.py --entity tasks
python tools/read-artifact-detail/scripts/run.py --path "<PATH>"
```

### 情况 4：用户要写新脚本或改写脚本
切到 `dy-script`。

### 情况 5：用户要生成视频或重生成视频
切到 `dy-render`。

## 约束

- 工具返回非零退出码时，不要假装成功
- 不要隐瞒环境变量缺失
- 只要工具层能记录任务状态和产物，就不要跳过
