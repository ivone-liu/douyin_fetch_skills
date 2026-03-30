---
name: douyin-shot-analysis-kb
description: 旧版知识库技能名的兼容适配器。适用于老流程仍调用这个名字的场景。新用法优先走 dy-kb。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧩", "category": "legacy"}}
---
# douyin-shot-analysis-kb

这是旧版 KB 技能名的兼容层。

## 建库
```bash
python tools/build-kb-from-md/scripts/run.py --creator-slug "<CREATOR_SLUG>"
```

## 查询
```bash
python tools/query-kb/scripts/run.py --creator-slug "<CREATOR_SLUG>" --query "<QUESTION>"
```

新入口优先使用 `dy-kb`。
