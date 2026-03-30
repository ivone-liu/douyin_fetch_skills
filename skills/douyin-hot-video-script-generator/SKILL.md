---
name: douyin-hot-video-script-generator
description: 旧版热门视频脚本生成器的兼容适配器。适用于仍使用老命令名生成脚本的场景。新用法优先走 dy-script。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧩", "category": "legacy"}}
---
# douyin-hot-video-script-generator

这是旧版脚本生成入口的别名。现在请直接执行：

```bash
python tools/generate-script-package/scripts/run.py --kb-json "<KB_JSON>" --request-json "<REQUEST_JSON>" --output "<OUTPUT_JSON_IF_NEEDED>"
```

生成完成后再保存版本：

```bash
python tools/save-script-version/scripts/run.py --creator-slug "<CREATOR_SLUG>" --mode "create_from_creator_style" --topic "<TOPIC>" --source-json "<GENERATED_JSON>"
```
