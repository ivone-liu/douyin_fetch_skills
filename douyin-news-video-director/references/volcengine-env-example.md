# Ark 图生视频最小环境变量

把下面内容放进 `~/.openclaw/.env`。

```bash
OPENCLAW_WORKSPACE_DATA_ROOT=~/.openclaw/workspace/data
ARK_API_KEY=你的_ARK_API_KEY
```

说明：

- `ARK_API_KEY` 是唯一必需的火山引擎配置。
- 生成接口、查询接口、请求方法、查询方法、模型名、任务状态解析路径，都已经在代码里固定为 Ark 图生视频这一套，不需要再手工配置。
- 当前模型固定使用：`doubao-seedance-1-5-pro-251215`
- 当前默认最大时长固定按 5 秒处理，对应你提供的接口示例。
