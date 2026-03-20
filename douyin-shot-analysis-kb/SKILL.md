---
name: douyin-shot-analysis-kb
description: Build, update, query, and maintain a reusable Douyin creative knowledge base from harvested creator videos and per-video analysis results. Use when the user asks to summarize filming techniques, extract repeatable patterns, maintain a creator playbook, compare content styles, or query existing Douyin knowledge for downstream generation.
compatibility: Works best in environments with exported Douyin video metadata, optional playable video URLs or downloaded files, a writable local file system, and code execution for producing structured KB files.
metadata:
  author: Ivone(ivone@nibbly.cn)
  version: 1.1.0
  category: document-asset-creation
  upstream: tikhub-douyin
---

# Douyin Shot Analysis Knowledge Base

This skill is responsible for turning harvested Douyin creator data into a persistent knowledge base that later skills can read.

## Current responsibility boundary

This skill should do four things:
1. define KB scope
2. build or update structured KB files
3. preserve evidence and sample references
4. answer questions from the KB or hand off to the script generator

This skill should not be used to subscribe creators or fetch raw videos. Use the dedicated upstream skills first.

## When to use this skill

Use this skill when the user wants to:
- analyze a creator's filming approach
- summarize hooks, pacing, framing, and transitions
- build a persistent inspiration library
- compare patterns across creators or categories
- ask questions based on existing analyzed creators

## Required inputs

Preferred inputs in order:
- normalized creator videos from the harvester skill
- optional per-video manual or model-assisted analysis results
- optional comments or engagement metrics
- optional user lens such as 电商带货, 口播, 探店, 母婴, 知识分享, vlog

## What counts as a real knowledge base

A real KB is not just one markdown summary.
It must have:
- creator identity
- dataset scope
- repeatable patterns
- evidence video ids
- optional metrics associations
- update timestamp
- reusable rules

## Knowledge base file layout

Preferred output layout:
- `kb/creator-slug/knowledge-base.json`
- `kb/creator-slug/knowledge-base.md`
- `kb/creator-slug/patterns.json`
- `kb/creator-slug/sample-index.json`

Optional upstream analysis inputs:
- `analysis/creator-slug/video-analysis.jsonl`
- `normalized/creator-slug/videos.json`

## Core workflow

### Step 1: Define scope
Choose one mode:
- single creator deep dive
- multi creator comparison
- topic cluster analysis
- top performing posts only
- recent content trend scan

State the scope explicitly.

### Step 2: Build evidence set
Start from normalized metadata.
If detailed video analysis exists, use it.
If only metadata exists, build a low-confidence KB and mark the missing depth clearly.

### Step 3: Normalize creator-level facts
Capture:
- creator profile
- content niche
- dominant formats
- sample count
- covered time range
- data confidence

### Step 4: Build pattern groups
Organize repeatable observations into:
- hooks
- shot language
- editing rhythm
- narrative templates
- packaging
- commercial intent
- anti-patterns

Each pattern must contain:
- `pattern_id`
- `category`
- `summary`
- `evidence_video_ids`
- `confidence`
- `reusability_note`
- `when_to_use`
- `when_not_to_use`

### Step 5: Save KB artifacts
Write both:
- machine-readable JSON
- human-readable markdown

Do not only save prose. The downstream script generation skill needs structured data.

### Step 6: Support querying
When the user asks questions such as:
- 这个账号最常见的开头是什么
- 哪些镜头最值得模仿
- 哪类结构最容易复用

Read `knowledge-base.json` and `patterns.json` first. Do not regenerate the KB unless needed.

## Quality bar

A good KB is:
- specific
- evidence-backed
- reusable
- updateable
- readable by both humans and downstream tools

A bad KB is vague praise or abstract content poetry.

## Hand-off rules

If there is no harvested data yet, stop and invoke the harvester skill first.
If the user wants a script or idea based on the KB, hand off to `douyin-hot-video-script-generator`.

## References to consult when needed

- `references/analysis-rubric.md`
- `references/kb-template.md`
- `references/knowledge-base-schema.md`
- `scripts/build_kb.py`
- `scripts/query_kb.py`

## Example triggers

Use this skill when users say things like:
- 分析这个抖音号的拍摄手法
- 基于这些视频做一个知识库
- 我已经抓完视频了，帮我沉淀成可复用的规则
- 读取这个账号的知识库，告诉我最常见的拍摄套路
