# 数据模型说明

## 本地数据根目录

默认写入：

```text
~/.openclaw/workspace/data/
```

可以通过 `OPENCLAW_WORKSPACE_DATA_ROOT` 覆盖。

## 关键数据

- `creators/`：按博主 slug 分目录保存
- `tasks/`：任务状态与步骤记录
- `registry/artifacts.jsonl`：产物登记
- `registry/scripts.json`：脚本版本登记
- `registry/renders.json`：渲染登记
- `registry/subscriptions.json`：订阅登记

## MySQL

SQL 文件兼容 MySQL 5.7，避免使用 8.0 独占特性。JSON 字段保留，但没有使用 JSON_TABLE、窗口函数、递归 CTE 等新特性。
