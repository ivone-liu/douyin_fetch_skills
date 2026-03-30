---
name: douyin-subscription-manager
description: 旧版订阅管理入口的兼容适配器。适用于仍使用老命令名做订阅、取消订阅、查看订阅状态或增量同步的场景。新用法优先走 dy-subscribe。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧩", "category": "legacy"}}
---
# douyin-subscription-manager

这是旧版订阅管理入口的兼容层。

它会把行为路由到 `dy-subscribe` 的新结构中，包括：

- 从主页 URL 订阅
- 查看订阅记录
- 执行增量同步
