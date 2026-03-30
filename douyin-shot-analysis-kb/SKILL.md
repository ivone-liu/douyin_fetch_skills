---
name: douyin-shot-analysis-kb
description: Build, update, query, and maintain a reusable Douyin creative knowledge base from harvested creator videos and per-video structured analyses. Use when the user asks to summarize filming techniques, extract repeatable patterns, maintain a creator playbook, compare content styles, or query existing Douyin knowledge for downstream generation.
compatibility: Works best in environments with exported Douyin video metadata, optional playable video URLs or downloaded files, writable local storage, and code execution for producing structured KB files.
metadata:
  author: OpenAI
  version: 2.0.0
  category: document-asset-creation
  upstream: tikhub-douyin
---

# Douyin Shot Analysis Knowledge Base

This skill turns harvested Douyin creator data and local per-video analyses into a persistent knowledge base that later skills can query.

## Current responsibility boundary

This skill should do five things:
1. define KB scope
2. build or update a Haystack + Qdrant RAG knowledge base and its manifest files
3. preserve evidence and sample references
4. keep a compact queryable video index
5. answer questions from the KB or hand off to the script generator

This skill should not subscribe creators or fetch raw videos. Use the dedicated upstream skills first.

## When to use this skill

Use this skill when the user wants to:
- analyze a creator's filming approach
- summarize hooks, pacing, framing, beats, dialogue, and transitions
- build a persistent inspiration library
- compare patterns across creators or categories
- ask questions based on existing analyzed creators

## Required inputs

Preferred inputs in order:
- local per-video markdown analyses under `analysis_md/`, ideally with an embedded structured JSON block
- normalized creator videos from the harvester skill
- optional per-video manual or model-assisted analysis results
- optional comments or engagement metrics
- optional user lens such as 电商带货, 口播, 探店, 母婴, 知识分享, vlog

## What counts as a real knowledge base

A real KB is not just one markdown summary.
It must have:
- creator identity
- dataset scope
- video index
- repeatable patterns
- evidence video ids
- optional metrics associations
- update timestamp
- reusable rules
- uncertainty and evidence depth

## Knowledge base file layout

Preferred output layout:
- `~/.openclaw/workspace/data/creators/creator-slug/kb/knowledge-base.json`
- `~/.openclaw/workspace/data/creators/creator-slug/kb/knowledge-base.md`
- `~/.openclaw/workspace/data/creators/creator-slug/kb/patterns.json`
- `~/.openclaw/workspace/data/creators/creator-slug/kb/sample-index.json`
- `~/.openclaw/workspace/data/creators/creator-slug/kb/video-index.json`

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
Start from local markdown analyses when available.
If a structured JSON block exists inside markdown, parse that first.
Use normalized metadata only as a secondary source.
If only metadata exists, build a low-confidence KB and mark the missing depth clearly.

### Step 3: Normalize creator-level facts
Capture:
- creator profile
- content niche
- dominant formats
- sample count
- covered time range
- source-depth breakdown
- data confidence

### Step 4: Build pattern groups
Organize repeatable observations into:
- goals
- archetypes
- hooks
- beats
- shot language
- dialogue tactics
- editing and packaging
- persuasion and CTA
- reusable formulas
- risks and anti-patterns

Each pattern must contain:
- `pattern_id`
- `category`
- `summary`
- `evidence_video_ids`
- `confidence`
- `reusability_note`
- `when_to_use`
- `when_not_to_use`
- `evidence_count`

### Step 5: Save KB artifacts
Write both:
- machine-readable JSON
- human-readable markdown

Do not only save prose.
The downstream script generation skill needs structured data.

### Step 6: Support querying
When the user asks questions such as:
- 这个账号最常见的开头是什么
- 哪些镜头最值得模仿
- 哪类结构最容易复用
- 最常见的话术动作是什么
- 什么情况下不要照抄这个账号

Read `knowledge-base.json` first to locate the Qdrant collection, then query through Haystack. Do not treat the JSON manifest itself as the KB body.

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
- `references/video-analysis-schema.md`
- `scripts/build_kb.py`
- `scripts/query_kb.py`

## Example triggers

Use this skill when users say things like:
- 分析这个抖音号的拍摄手法
- 基于这些视频做一个知识库
- 我已经抓完视频了，帮我沉淀成可复用的规则
- 读取这个账号的知识库，告诉我最常见的拍摄套路

## Source priority

For downstream reasoning, prefer this order:
1. per-video structured JSON blocks inside local markdown analysis files
2. per-video local markdown analysis prose
3. normalized json
4. raw API json

This ordering prevents repeated re-interpretation of raw payloads.


## RAG storage rule

The canonical KB lives in Qdrant.
`knowledge-base.json` is a manifest, not the full knowledge base body.
