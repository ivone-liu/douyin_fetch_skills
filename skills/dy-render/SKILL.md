---
name: dy-render
description: 提交、重试和查看火山引擎视频生成任务。适用于用户已经有脚本或渲染请求、需要真正生成视频、查看渲染状态或在原任务基础上附加修改要求重新生成的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🎥", "category": "workflow"}}
---
# dy-render

当用户要真正生成视频时，使用这个技能。

## 提交渲染任务
```bash
python tools/submit-render-task/scripts/run.py --request-json "<REQUEST_JSON>" --download-results
```

## 重试或做变体
```bash
python tools/retry-render-task/scripts/run.py --render-task-id "<RENDER_TASK_ID>" --notes "<CHANGE_REQUEST>"
```

## 重要约束

- 需要图生视频链路时，不要在缺少可用参考图的情况下盲目提交
- 说清楚这是旧新闻导演链路，还是直接调用火山渲染
