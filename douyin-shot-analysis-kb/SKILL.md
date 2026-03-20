---
name: douyin-shot-analysis-kb
description: Analyze Douyin short videos for shooting methods, editing patterns, hooks, scene structure, and repeatable content techniques, then generate a structured knowledge base. Use when the user asks to study a creator's filming style, extract reusable creative tactics, summarize patterns across many Douyin videos, or build a reusable playbook from crawled video data.
compatibility: Works best in environments with exported Douyin video metadata, optional access to playable video URLs or downloaded files, a writable local file system, and code execution for post-processing summaries.
metadata:
  author: OpenAI
  version: 1.0.0
  category: document-asset-creation
  upstream: tikhub-douyin
---

# Douyin Shot Analysis Knowledge Base

This skill turns raw Douyin video datasets into reusable creative knowledge.

## When to use this skill

Use this skill when the user wants to:
- analyze a creator's filming approach
- break down hooks, pacing, framing, and transitions
- summarize repeatable content techniques across many posts
- build an internal inspiration library or playbook
- compare patterns across creators or content buckets

Do not use this skill to fetch creator videos. Use the harvester first.

## Inputs

Preferred inputs:
- normalized video dataset from the harvester skill
- playable video URLs or local video files for deeper inspection
- optional comments or engagement metrics
- optional user lens such as 电商带货, 口播, 探店, 母婴, 知识分享, 或 vlog

## Output goals

Produce a knowledge base that is useful, not decorative. It should answer:
- what this creator repeatedly does
- how they open, pace, and close videos
- which techniques appear often enough to be replicable
- which patterns correlate with stronger engagement
- what can be reused by another team without copying surface style blindly

## Core workflow

### Step 1: Define the analysis scope
Choose one of these modes:
- single creator deep dive
- multi creator comparison
- topic cluster analysis
- top performing posts only
- recent content trend scan

State the scope explicitly before analyzing.

### Step 2: Build the analysis sample
Start from normalized metadata.
If full playback is available, inspect a representative sample rather than every video frame of every post.
Recommended sampling order:
1. top engagement posts
2. recent posts
3. median posts
4. outliers that break the normal pattern

### Step 3: Analyze across these dimensions
For each video or sampled subset, extract observations for:

#### Hook design
- opening line pattern
- first three-second visual action
- whether the hook is conflict, surprise, utility, identity, or curiosity

#### Shot language
- camera distance, such as close-up, medium, wide
- camera stability, such as tripod, handheld, moving follow
- angle choice, such as eye-level, top-down, low-angle
- subject framing and headroom
- use of cut-ins or product detail shots

#### Editing rhythm
- average shot duration
- hard cuts versus masked transitions
- caption density
- pacing changes around payoff moments
- looping or callback endings

#### Scene and narrative structure
- common scene templates
- whether there is a setup, conflict, payoff arc
- whether the creator uses scripted beats or conversational drift

#### Audio layer
- speech intensity and cadence
- music role, such as emotional bed or trend support
- use of sound effects for emphasis

#### Packaging
- cover image style
- title pattern
- hashtag behavior
- series behavior, recurring formats, or episodic structures

#### Commercial or strategic intent
- call to action type
- trust-building device
- proof element, such as demo, testimonial, before-after, or authority cue

### Step 4: Turn observations into reusable rules
Move from observation to principle.
For every important pattern, write:
- observed pattern
- why it works here
- when to reuse it
- when not to reuse it
- minimal implementation recipe

Reject empty conclusions such as `节奏很好` or `镜头丰富`. Convert them into measurable statements.

### Step 5: Build the knowledge base
Organize the final KB into these sections:
1. creator profile and content positioning
2. recurring shot and edit patterns
3. hook library
4. structure templates
5. high-performing motif map
6. practical playbook
7. anti-patterns and limits
8. next experiments

### Step 6: Connect patterns to metrics
Whenever engagement data exists, correlate pattern frequency with:
- play count
- like rate
- comment rate
- collect rate
- share rate

Avoid claiming causality unless the evidence is strong. Frame it as a pattern association when needed.

## Quality bar

A good analysis should be:
- specific
- transferable
- falsifiable
- tied to evidence
- useful to a content operator

A bad analysis is vague trend poetry.

## Deliverable formats

Preferred outputs:
- concise markdown knowledge base
- structured JSON facts for downstream systems
- creator playbook table for operators
- cross-creator comparison memo

## Recommended file layout

- `kb/creator-slug/knowledge-base.md`
- `kb/creator-slug/patterns.json`
- `kb/creator-slug/sample-index.json`

## Hand-off rules

If the user has not yet crawled the creator's videos, stop and ask for the harvested dataset or invoke the harvester skill first.
If the user wants a persistent inspiration library, recommend keeping one KB file per creator and one synthesis file per category.

## References to consult when needed

- `references/analysis-rubric.md`
- `references/kb-template.md`
- `scripts/build_kb.py`

## Example triggers

Use this skill when users say things like:
- 分析这个抖音号的拍摄手法
- 提炼这个博主的内容套路
- 给我总结他的镜头语言和剪辑方式
- 基于这些视频做一个知识库
- 对比几个账号的拍摄技巧
