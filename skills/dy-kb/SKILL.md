---
name: dy-kb
description: 构建或查询博主风格知识库，适用于用户要把分析报告写入 KB、检索某个博主的风格特征、或为脚本生成提供参考案例的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧠", "category": "reasoning"}}
---
# dy-kb

当你要处理“风格知识库”时，使用这个技能。

## 从分析 Markdown 建库
```bash
python tools/build-kb-from-md/scripts/run.py --creator-slug "<CREATOR_SLUG>"
```

## 查询知识库
```bash
python tools/query-kb/scripts/run.py --creator-slug "<CREATOR_SLUG>" --query "<QUESTION>"
```

## 约束

- 优先基于经过 review 的分析结果建库
- 不要宣称自己验证过 KB 新鲜度，除非你真的验证过
