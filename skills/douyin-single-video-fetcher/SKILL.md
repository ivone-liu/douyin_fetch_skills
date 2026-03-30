---
name: douyin-single-video-fetcher
description: 旧版单视频抓取入口的兼容适配器。适用于用户还在使用旧技能名，或已有流程里仍调用这个名字的场景。新用法优先改走 dy-ingest。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧩", "category": "legacy"}}
---
# douyin-single-video-fetcher

这是旧版单视频入口的兼容层。

## 推荐新路径

```bash
python tools/fetch-single-video-payload/scripts/run.py --source "<SOURCE>" --output /tmp/douyin_single_video.json
python tools/ingest-video-payload/scripts/run.py --input-json /tmp/douyin_single_video.json --source-input "<SOURCE>" --run-analysis
```

如果不是为了兼容旧命令名，优先使用 `dy-ingest`。
