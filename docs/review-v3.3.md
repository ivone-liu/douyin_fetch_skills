# v3.3 review 记录

## 本次重点修复

1. 切换到 Python 3.10+ 主线依赖
   - haystack-ai >= 2.22
   - qdrant-haystack >= 10
   - qdrant-client >= 1.15

2. 修复 ingest -> analysis 参数不匹配
   - 旧问题：pipeline 只传 normalized_json 路径给 wrapper，但 wrapper 只接受 --video / --creator-slug
   - 现修复：wrapper 同时支持 `--normalized-json` 与兼容的 `--video` 模式；pipeline 改为显式传 `--normalized-json`

3. 修复 OpenAI-compatible 本地无鉴权网关可用性
   - 允许“有 base URL + model、没有 API key”的场景
   - 内部对 `api_key` 回退到占位 token `not-needed`

4. 更新安装与文档
   - install.sh 改为检查 Python >= 3.10
   - README / how_to_use / Project / .env.example 全部同步为 v3.3 主线版说明

## review 轮次

- 第一轮：依赖矩阵 review
- 第二轮：pipeline 参数链 review
- 第三轮：本地 smoke test + 安装后验证
