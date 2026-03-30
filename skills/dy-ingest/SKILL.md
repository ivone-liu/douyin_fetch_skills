---
name: dy-ingest
description: 把单条抖音视频接入系统，支持 URL、aweme_id、已有 payload JSON 或本地文件模式。适用于用户要分析一条视频、把视频写入本地资产库、或希望后续继续做知识库和脚本工作的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "📥", "category": "workflow"}}
---
# dy-ingest

当用户要把一条视频正式纳入系统时，使用这个技能。

## 支持模式

- 单条 URL 或分享文案
- aweme_id
- 已有 payload JSON
- 本地视频文件 + 元数据

## 推荐路径

### URL 或分享文案
```bash
python tools/fetch-single-video-payload/scripts/run.py --source "<SOURCE>" --output /tmp/douyin_single_video.json
python tools/ingest-video-payload/scripts/run.py --input-json /tmp/douyin_single_video.json --source-input "<SOURCE>" --run-analysis
```

### 已有 payload JSON
```bash
python tools/ingest-video-payload/scripts/run.py --input-json "<PAYLOAD_JSON>" --source-input "manual-payload" --run-analysis
```

### 只有本地文件
如果用户已经有本地视频文件，跳过 payload 接入，直接用 `dy-video-analysis`。

## 预期输出

- raw payload 路径
- normalized payload 路径
- 本地下载的视频/音乐路径（如果可用）
- 分析报告与证据文件（如果开启 `--run-analysis`）
