---
name: douyin-skills-v3-1
description: 抖音内容工作流技能包，负责在视频接入、博主订阅、资源查询、风格分析、知识库构建与检索、脚本生成、脚本改写、审核和视频渲染之间进行路由。适用于用户给出抖音视频链接、要求订阅博主、查看资产、按博主风格生成脚本、重写脚本或提交视频生成任务的场景。这个根技能用于兼容只识别根目录 SKILL.md 的宿主，并引导到 skills/ 下的专用技能。
compatibility: OpenClaw 或任何兼容 AgentSkills 的宿主。支持根技能目录模式和 workspace 子技能模式；RAG 侧支持 Haystack + Qdrant 的 server、local、memory 三种运行方式，并可通过 OpenClaw 提供的 OpenAI 兼容模型端点执行检索后生成。
metadata:
  author: OpenAI-assisted redesign
  version: 3.1.0
  package_type: skill-pack
  entry_skills:
    - dy-flow
    - dy-ingest
    - dy-subscribe
    - dy-library
    - dy-script
    - dy-render
    - dy-video-analysis
    - dy-kb
    - dy-review
---
# 抖音 Skills v3.3

这个根技能的作用，不是替代 `skills/` 里的子技能，而是确保在“只识别根目录技能”的宿主里，这个包也能被识别和激活。

## 你应该先看什么

1. `Project.md`：看整体设计、分层与数据流
2. `how_to_use.md`：看安装方式、环境变量和常见工作流
3. `skills/dy-flow/SKILL.md`：输入不明确时，优先用它做总控路由

## 根技能应该怎么用

- 当用户只丢来一个抖音链接，不明确要分析、订阅、写脚本还是渲染时，先交给 `dy-flow`
- 当用户明确想做某一步时，直接转给对应子技能
- 当用户仍使用旧 skill 名称时，直接映射到当前 v3 工具
- 当用户明确要走本地 RAG 时，优先采用：
  - `HAYSTACK_QDRANT_MODE=server` + 本机 `QDRANT_URL`
  - 或 `HAYSTACK_QDRANT_MODE=local` + `HAYSTACK_QDRANT_PATH`

## 约束

- 不要把所有事都挤进一个 skill
- 创作与执行要分开
- 能写入任务状态和产物登记的步骤必须写
- 本地 RAG 优先走 `server` 或 `local`，`memory` 只用于测试
