Suggested request.json shape:

```json
{
  "news_title": "某条新闻标题",
  "news_summary": "用两三句话说明发生了什么",
  "audience": "你希望视频触达的人",
  "goal": "提高完播和互动",
  "voice_tone": "冷静、直接、有判断",
  "angle": "可选，你想强调的观点",
  "takeaway": "可选，结尾结论",
  "cta": "可选，收尾动作",
  "aspect_ratio": "9:16",
  "duration_seconds": 5,
  "reference_image_url": "https://.../cover.png",
  "camera_fixed": false,
  "watermark": true,
  "negative_prompt": "可选",
  "submit_video": true,
  "kb_paths": [
    "~/.openclaw/workspace/data/creators/creator-a/kb/knowledge-base.json"
  ]
}
```

说明：
- `reference_image_url` 是 Ark 图生视频提交时的必要输入。
- 如果只想先出脚本包，不想提交视频，可以把 `submit_video` 设为 `false` 或命令行加 `--no-submit`。


补充说明：当前 Ark 图生视频模型固定使用 `doubao-seedance-1-5-pro-251215`，不需要在请求中再传模型配置。
