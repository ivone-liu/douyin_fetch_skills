---
name: dy-script
description: 生成、改写并保存脚本，适用于基于博主风格、主题、新闻事件生成新脚本，或对已有脚本进行重写、压缩、扩展和变体改造的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "📝", "category": "workflow"}}
---
# dy-script

当用户要写脚本、改脚本、复用风格写脚本时，使用这个技能。

## 主要路径

### 基于博主风格或主题生成脚本
如果请求与旧版热门视频脚本生成器兼容，可以走：

```bash
python tools/generate-script-package/scripts/run.py --kb-json "<KB_JSON>" --request-json "<REQUEST_JSON>" --output "<OUTPUT_JSON_IF_NEEDED>"
```

然后落版本：

```bash
python tools/save-script-version/scripts/run.py --creator-slug "<CREATOR_SLUG>" --mode "<MODE>" --topic "<TOPIC>" --source-json "<GENERATED_JSON>" --source-md "<GENERATED_MD_IF_ANY>"
```

### 新闻型脚本包
如果用户明确要新闻视频脚本包，可走旧新闻导演脚本生成，但先不直接提交渲染：

```bash
python tools/generate-news-video-package/scripts/run.py --request-json "<REQUEST_JSON>" --no-submit
```

生成后仍然要保存版本。

## 规则

- 脚本是版本化产物，不是一次性聊天文本
- 只要脚本有复用价值，就保存版本
- 不确定质量时，先交给 `dy-review`
