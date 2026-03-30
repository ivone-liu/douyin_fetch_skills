---
name: douyin-news-video-director
description: 旧版新闻视频导演入口的兼容适配器。适用于老流程仍使用这个名字做脚本加渲染一体化处理的场景。新用法优先拆成 dy-script、dy-review、dy-render 三段。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧩", "category": "legacy"}}
---
# douyin-news-video-director

这是旧版新闻导演入口的别名。现在推荐拆成脚本包生成与渲染两步：

```bash
python tools/generate-news-video-package/scripts/run.py --request-json "<REQUEST_JSON>" --no-submit
```

需要直接渲染时，再调用：

```bash
python tools/submit-render-task/scripts/run.py --request-json "<RENDER_REQUEST_JSON>" --download-results
```
