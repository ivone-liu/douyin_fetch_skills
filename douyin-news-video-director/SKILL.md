---
name: douyin-news-video-director
description: Read one or more existing Douyin knowledge bases, turn a supplied news event into a fresh short-video angle, generate a complete beat-by-beat script and shot plan, and submit the final video prompt to Volcengine for direct video generation. Use when the user wants to go from news topic to publishable short video, not just to a text script.
compatibility: Works best in environments with readable local KB files under ~/.openclaw/workspace/data, writable workspace storage, and Volcengine video generation credentials configured in ~/.openclaw/.env.
metadata:
  author: OpenAI
  version: 1.0.0
  category: workflow-automation
  upstream: douyin-shot-analysis-kb
---

# Douyin News Video Director

This skill is the bridge from news input to finished AI-generated video.

## Use this skill when

Use this skill when the user wants to:
- give you a news event and get a new short-video angle
- read all relevant KBs before deciding the script structure
- generate a complete beat-by-beat script and shot plan
- produce a model-ready video prompt
- call Volcengine video generation and save the result locally

Do not use this skill if no KB exists yet. Build or update KBs first.

For Ark 图生视频 submission, provide a reachable `reference_image_url` in request.json.

## Storage policy

All outputs must go under:
- `~/.openclaw/workspace/data/`

Creator-grouped outputs stay under:
- `~/.openclaw/workspace/data/creators/<creator-slug>/...`

For this skill, save to:
- `generated_scripts/news_video/<timestamp>_<slug>.json`
- `generated_scripts/news_video/<timestamp>_<slug>.prompt.txt`
- `generated_scripts/news_video/<timestamp>_<slug>.md`
- `generated_videos/news_video/<timestamp>_<slug>/...`

Never write generated assets back into the skill-pack directory.

## Required reasoning order

### Step 1: read KBs first
Read all relevant `knowledge-base.json` files before proposing a new video idea.
Prefer KB evidence over intuition.
If the user did not specify KB paths, scan:
- `~/.openclaw/workspace/data/creators/*/kb/knowledge-base.json`

### Step 2: do not merely restate the news
You must transform the news into a video angle.
That means extracting:
- the sharpest hook
- the most transferable structure
- the right emotional lever
- the most suitable shot language for this topic

### Step 3: generate a full package
The output package must include:
- topic angle
- hook line
- beat-by-beat script
- shot plan
- on-screen text direction
- model-ready Volcengine prompt
- negative prompt
- uncertainty and fit notes

### Step 4: submit to Volcengine
Use the helper script and the env in `~/.openclaw/.env`.
Read `ARK_API_KEY` from env. Do not require extra VOLCENGINE_VIDEO_* configuration for the Ark path.
Use the Ark task submit endpoint and task query endpoint.
Do not hardcode secrets into the skill instructions.

### Step 5: save everything
Always save the script package and the generation response locally.
If the generation succeeds, download the result video into the creator subtree.

## Core guardrails

- never ignore the KB and jump straight to generic news narration
- never claim the generated video is final-quality without review
- never hardcode provider secrets
- never write output into repo-local `data/`
- never promise exact camera motion fidelity from text-to-video generation

## Suggested script

Primary helper:
- `scripts/generate_news_video.py`

References:
- `references/news-video-request-schema.md`
- `references/volcengine-env-example.md`

## Example trigger

Use this skill when users say things like:
- 给你一条新闻，基于知识库做成一条视频
- 读取全部知识库，帮我出一个新闻短视频脚本并直接生成视频
- 用现有拍摄方法库，把这条新闻转成一条可以直接发的抖音视频
