---
name: dy-video-analysis
description: 对本地视频做深度分析，并产出人类可读报告与证据文件。适用于视频资产已经存在、本地需要做节奏、镜头、结构和风格拆解的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🔬", "category": "reasoning"}}
---
# dy-video-analysis

当本地视频已经存在，需要做结构化分析时，使用这个技能。

## 命令

```bash
python tools/analyze-local-video/scripts/run.py --video "<VIDEO_PATH>" --creator-slug "<CREATOR_SLUG>" --video-id "<VIDEO_ID>" --desc "<DESC>"
```

## 输出类型

- 人类可读 Markdown 报告
- analysis evidence JSON
- contact sheet / keyframe 结果（如果旧分析器产出）

## 解释规则

请明确区分：

- hard evidence
- inferred patterns
- speculative hypotheses
