---
name: douyin-video-analysis
description: 旧版深度视频分析入口的兼容适配器。适用于老流程仍调用这个名字的场景。新用法优先走 dy-video-analysis。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧩", "category": "legacy"}}
---
# douyin-video-analysis

这是旧版深度分析入口的兼容层。

推荐执行：

```bash
python tools/analyze-local-video/scripts/run.py --video "<VIDEO_PATH>" --creator-slug "<CREATOR_SLUG>" --video-id "<VIDEO_ID>" --desc "<DESC>"
```

新入口优先使用 `dy-video-analysis`。
