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
  "duration_seconds": 12,
  "negative_prompt": "可选",
  "kb_paths": [
    "~/.openclaw/workspace/data/creators/creator-a/kb/knowledge-base.json"
  ],
  "submit_video": true
}
```
