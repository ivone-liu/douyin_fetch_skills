---
name: douyin-hot-video-script-generator
description: Read existing Douyin creator knowledge bases and generate a practical short-video script tailored to the user's goal, audience, product, and tone. Use when the user asks to create a potentially high-performing video script based on previously extracted patterns, without blindly copying a creator.
compatibility: Works best in environments with access to the local KB directory, writable output files, and optional code execution for filling a JSON or markdown script template.
metadata:
  author: OpenAI
  version: 1.0.0
  category: creative-generation
  upstream: douyin-shot-analysis-kb
---

# Douyin Hot Video Script Generator

This skill reads creator knowledge bases and turns proven patterns into a usable script draft.

## When to use this skill

Use this skill when the user wants to:
- generate a short-video script from an existing creator KB
- adapt a creator style to a new product or niche
- produce several script options from proven hooks and structures
- create a hot-video draft grounded in evidence instead of vague inspiration

Do not use this skill until a usable KB exists.

## Required inputs

Prefer these inputs:
- local per-video markdown analyses under `analysis_md/`
- `knowledge-base.json` or `patterns.json`
- user goal
- target audience
- product or topic
- desired tone
- desired duration or approximate video length
- constraints such as no露脸, low budget, single location, or口播 only

## Core workflow

### Step 1: Read local markdown and KB before generating
Inspect:
- repeated hooks
- repeated structures
- reusable shot-language patterns
- anti-patterns
- playbook notes
- per-video local markdown notes

Do not generate from memory when markdown or KB files are available.

### Step 2: Translate user need into generation constraints
Capture:
- content objective
- who the audience is
- what action the audience should take
- what proof or trust element is available
- what production constraints exist

### Step 3: Select only transferable patterns
Use patterns with strong evidence and relevance.
Reject patterns that depend on:
- a very specific creator persona
- resources the user does not have
- tone that conflicts with the user's brand

### Step 4: Generate a grounded script
The output should include:
- title or topic angle
- hook
- beat-by-beat script
- suggested shots
- on-screen text
- CTA
- why this draft fits the KB

### Step 5: Mark uncertainty honestly
State where the script is grounded in KB evidence and where it is an inference.
Do not claim the script will definitely go viral.

## Output formats

Preferred outputs:
- markdown script brief
- JSON script schema for downstream editing tools
- 3-option idea set with one recommended option

## Hand-off rules

If the KB is missing or too weak, stop and call the KB skill first.
If the user needs multiple variants, generate 3 options with different hook strategies.

## References to consult when needed

- `references/script-template.md`
- `references/script-schema.md`
- `scripts/generate_script.py`

## Example triggers

Use this skill when users say things like:
- 读取这个知识库，帮我写一条短视频脚本
- 基于这个博主的套路，给我生成一个适合我产品的视频脚本
- 不要抄，参考知识库写一个更适合我用户的视频
