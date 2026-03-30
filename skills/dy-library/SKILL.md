---
name: dy-library
description: 统一查看本地 workspace 中的 creators、tasks、artifacts、scripts 和 renders。适用于用户要查看已经抓到哪些博主、哪些任务已完成、某个脚本是否存在、或要读取某个具体文件内容的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🗂️", "category": "workflow"}}
---
# dy-library

当用户要查看系统里已经有什么时，使用这个技能。

## 常用命令

```bash
python tools/list-library-entities/scripts/run.py --entity creators
python tools/list-library-entities/scripts/run.py --entity tasks
python tools/list-library-entities/scripts/run.py --entity artifacts
python tools/list-library-entities/scripts/run.py --entity scripts
python tools/list-library-entities/scripts/run.py --entity renders
```

读取具体文件：

```bash
python tools/read-artifact-detail/scripts/run.py --path "<PATH>"
```

## 约束

- 缺失的文件不要瞎编
- 先读已有产物，再决定是否重跑昂贵步骤
