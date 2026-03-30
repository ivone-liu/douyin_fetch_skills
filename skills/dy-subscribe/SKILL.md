---
name: dy-subscribe
description: 管理博主订阅、主页作品同步与增量更新。适用于用户要根据主页 URL 建立订阅、同步博主历史内容、查看订阅记录或执行增量同步的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "📡", "category": "workflow"}}
---
# dy-subscribe

当用户要做“博主级别”的采集时，使用这个技能。

## 常用动作

### 根据主页 URL 订阅或同步
```bash
python tools/fetch-creator-feed/scripts/run.py --profile-url "<PROFILE_URL>" --max-pages 2
```

### 增量同步
```bash
python tools/sync-creator-incremental/scripts/run.py --profile-url "<PROFILE_URL>"
```

### 查看订阅记录
读取 `~/.openclaw/workspace/data/registry/subscriptions.json`，或通过 `dy-library` 查看相关 creator 和 task。

## 说明

这个包不会掩盖一个事实：远程抓取依赖 TikHub 令牌和接口可用性。
