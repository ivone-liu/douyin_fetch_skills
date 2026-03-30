---
name: dy-review
description: 在脚本生成和视频渲染之间做质量闸门，检查风格一致性、信息密度、镜头可拍性和风险。适用于用户已经有脚本，但不想直接花渲染成本，希望先做导演视角 review 的场景。
user-invocable: true
disable-model-invocation: false
metadata: {"openclaw": {"emoji": "🧪", "category": "reasoning"}}
---
# dy-review

这是脚本到渲染之间的质量闸门。

## review 清单

- 脚本真的贴合目标博主风格吗？
- 开头钩子够不够强？
- 信息密度是否适合目标时长？
- 文字能否真的转成镜头？
- 是否存在事实风险、平台风险或合规风险？

## 配合方式

- 先用 `dy-library` 读取脚本产物
- 再用 `dy-kb` 取回风格参考
- review 后再决定是否进入 `dy-render`
