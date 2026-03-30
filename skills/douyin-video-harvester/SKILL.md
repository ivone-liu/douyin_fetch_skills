---
name: douyin-video-harvester
description: 旧版博主采集入口的兼容适配器。适用于旧流程仍在调用这个名字的场景。新用法优先改走 dy-subscribe。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧩", "category": "legacy"}}
---
# douyin-video-harvester

这是旧版博主采集入口的兼容层。

## 推荐新路径

```bash
python tools/fetch-creator-feed/scripts/run.py --profile-url "<PROFILE_URL>" --max-pages 2
```

后续增量同步：

```bash
python tools/sync-creator-incremental/scripts/run.py --profile-url "<PROFILE_URL>"
```

新入口请优先使用 `dy-subscribe`。
