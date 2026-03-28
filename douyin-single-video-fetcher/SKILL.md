---
name: douyin-single-video-fetcher
description: Fetch one Douyin video via TikHub, persist the raw API response locally, extract high-value media fields into MySQL, download grouped video and music assets, and generate one local markdown analysis document per video. Use when the user wants a single-post ingestion pipeline instead of a full-account crawl.
compatibility: Works best in environments with TikHub API access, outbound network access, secure secret storage for TIKHUB_API_TOKEN, a writable local file system, and optional MySQL access through MYSQL_DSN.
metadata:
  author: OpenAI
  version: 2.0.0
  category: workflow-automation
  upstream: tikhub-douyin
---

# Douyin Single Video Fetcher

This skill is no longer just a one-post metadata fetcher.
It is the entry point for a single-video local ingestion pipeline.

## Use this skill when

Use this skill when the user wants to:
- fetch one Douyin video by `aweme_id`, share URL, or share text
- keep the full TikHub response as a local JSON record
- extract video URL and music URL into MySQL
- download video and music into grouped local folders
- generate a dedicated local markdown analysis file for the video
- embed a structured analysis JSON scaffold inside that markdown file
- analyze downstream tasks by reading local markdown instead of raw JSON

Do not use this skill when the user wants the entire creator history. Use `douyin-video-harvester` for that.

## Input priority

Accept these inputs in this order:
1. `aweme_id`
2. single video share link
3. copied share text that contains exactly one target link
4. full Douyin single-post URL

## Output contract

This skill should produce all of the following where possible:
- a raw API response JSON file
- a normalized single-video JSON file
- MySQL rows for video and music indexing
- grouped local downloads for video and music
- one markdown analysis document for the specific video

## Local file policy

Use the OpenClaw workspace data root instead of repo-local storage.
The pipeline writes to:
- `~/.openclaw/workspace/data/creators/<creator-slug>/...`

You can override the root with `OPENCLAW_WORKSPACE_DATA_ROOT` when needed.

Treat creator storage as three layers:

### Layer 1: raw evidence
Store the full TikHub response unchanged under:
- `~/.openclaw/workspace/data/creators/<creator-slug>/raw_api/douyin_single_video/<date>/<video_id>.json`

### Layer 2: normalized record
Store a compact normalized view under:
- `~/.openclaw/workspace/data/creators/<creator-slug>/normalized/douyin_single_video/<video_id>.json`

### Layer 3: analysis document
Store one markdown file per video under:
- `~/.openclaw/workspace/data/creators/<creator-slug>/analysis_md/<video_id>.md`

Downloads live alongside those layers under:
- `~/.openclaw/workspace/data/creators/<creator-slug>/downloads/videos/<video_id>.*`
- `~/.openclaw/workspace/data/creators/<creator-slug>/downloads/music/<music-key>.*`

Downstream analysis should read the markdown file first.
The raw JSON is for traceability, not for repeated semantic analysis.

## MySQL storage policy

Do not dump the full raw payload into MySQL.
Use MySQL for high-value searchable fields only.

Store at least:
- creator identity
- `aweme_id`
- `play_url`
- `music_play_url`
- local file paths
- raw JSON path
- normalized JSON path
- markdown analysis path
- download and analysis status

## Core workflow

### Step 1: resolve one target
Resolve the input into exactly one stable `aweme_id`.
Stop on ambiguity.

### Step 2: fetch one video detail from TikHub
Use the most complete single-video endpoint available.
Capture the endpoint name and source input for traceability.

### Step 3: save the raw response immediately
Do not wait until normalization succeeds.
The raw response must be stored first.

### Step 4: normalize key fields
Normalize:
- creator ids
- video metadata
- video play URL
- music metadata
- timestamps
- engagement fields

### Step 5: upsert MySQL index rows
Write or update rows in:
- `creators`
- `videos`
- `music_assets`
- `video_music_map`
- `api_fetch_logs`

### Step 6: download media assets
Download:
- the main video file
- the music file when a valid music play URL exists

Group them by creator slug.

### Step 7: update paths and statuses
After download, update MySQL with:
- `local_video_path`
- `local_music_path`
- `download_status`
- `downloaded_at`

### Step 8: generate one markdown analysis file
As soon as download finishes, generate a markdown analysis file with:
- source metadata
- local file paths
- script summary
- hook hypothesis
- content archetype guess
- structured beat scaffold
- structured shot-plan scaffold
- editing and persuasion placeholders
- music notes
- uncertainty statement
- one embedded structured JSON block for downstream KB building

### Step 9: future analysis reads markdown first
Any downstream query, KB build, or script generation should read the local markdown file before falling back to raw JSON.

## Suggested scripts

Use these helpers together:
- `scripts/fetch_single_video.py`
- `scripts/pipeline_ingest_single_video.py`
- `scripts/read_local_md.py`

## Required environment variables

Recommended:
- `TIKHUB_API_TOKEN`
- `MYSQL_DSN`

## Database schema

Use the SQL file in:
- `db/douyin_media_schema.sql`

## Guardrails

- never overwrite raw API evidence silently
- never claim visual analysis certainty when only metadata exists
- never treat local markdown as source truth if the referenced raw JSON is missing
- never confuse one-video ingestion with creator-wide crawling
