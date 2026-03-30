---
name: douyin-video-harvester
description: Fetch all short videos from one or more Douyin accounts through TikHub with pagination, normalization, deduplication, and export. Use when the user asks to crawl every post from a Douyin creator, backfill an account, sync all videos from a monitored creator, or export a creator's full posting history.
compatibility: Works best in environments with TikHub API access, outbound network access, secure secret storage for TIKHUB_API_TOKEN, and a writable local file system for JSON or CSV exports.
metadata:
  author: OpenAI
  version: 1.1.0
  category: workflow-automation
  upstream: tikhub-douyin
---

# Douyin Video Harvester

This skill fetches the full post history for a Douyin creator and prepares structured output for later analysis.

## When to use this skill

Use this skill when the user wants to:
- grab all short videos from a creator
- backfill a monitored account
- export post history to JSON or CSV
- sync new videos incrementally after a previous crawl
- prepare source data for creative analysis and knowledge-base generation

Do not use this skill for follow or unfollow actions. Do not use it for creative analysis beyond lightweight metadata enrichment.

## Inputs

Preferred creator identifiers:
1. `sec_user_id`
2. `unique_id`
3. share link or profile URL

Optional crawl controls:
- `count_per_page`, default 20
- `max_items`, optional ceiling
- `since_timestamp`, optional incremental sync lower bound
- `subscription_mode`, optional, one of `backfill_all` or `latest_only`
- `subscription_started_at`, required when `subscription_mode = latest_only`
- `include_comments`, default false
- `include_play_url`, default true
- `output_format`, one of json or csv

## Core workflow

### Step 1: Resolve identity
Normalize the creator to a stable identity before crawling.
Store:
- `display_name`
- `sec_user_id`
- `unique_id`
- `uid`
- `avatar_url`
- `signature`

### Step 2: Choose the TikHub post-list endpoint
Prefer the most suitable homepage-video endpoint documented by TikHub for Douyin web or app.
The public docs explicitly list `Get user homepage video data` and multiple variants, plus related utility endpoints for profile resolution and play URL enrichment.

Prefer this order:
1. stable homepage video endpoint with full metadata
2. faster simplified homepage endpoint when the user only needs a bulk catalog
3. app endpoint variant if the web endpoint is rate-limited or field coverage is inadequate

### Step 3: Crawl with pagination
Initialize:
- `max_cursor = 0`
- `has_more = true`

Loop until one of these is true:
- the endpoint returns no items
- `has_more` is false
- `max_items` limit is reached
- the latest fetched item is older than `since_timestamp` during incremental sync
- in `latest_only` mode, the fetched items are all older than `subscription_started_at`

On each page:
1. request one page
2. validate that the returned creator identity still matches the target
3. normalize each video item
4. deduplicate by `aweme_id` or equivalent stable video id
5. append to the result set
6. advance `max_cursor`

### Step 4: Normalize fields
Produce one normalized item per video with these fields where available:
- `video_id`
- `desc`
- `create_time`
- `author_sec_user_id`
- `author_unique_id`
- `author_name`
- `duration_ms`
- `digg_count`
- `comment_count`
- `collect_count`
- `share_count`
- `play_count`
- `cover_url`
- `play_url`
- `music_title`
- `music_author`
- `mix_id`
- `is_pinned`
- `raw_page_cursor`
- `crawl_time`

Preserve a `raw` field only when the user explicitly wants the untouched response. Otherwise keep exports lean.

### Step 5: Enrich if needed
If the user asks for best possible playback or later video analysis, enrich with high-quality play URLs using the dedicated TikHub play-url endpoint.
Only fetch comments if the user explicitly asks, because it increases crawl time and cost.

### Step 6: Export
Write results to one or more of:
- `exports/creator-slug/videos.json`
- `exports/creator-slug/videos.csv`
- `exports/creator-slug/crawl-metadata.json`

The crawl metadata file should include:
- creator identity
- endpoint used
- page count
- total videos
- started_at
- finished_at
- errors
- incomplete flag

## Validation rules

- Never mix videos from different creators in one crawl result.
- Stop immediately if identity drift is detected.
- Retry transient failures with bounded backoff.
- After repeated failure, save a partial result with `incomplete = true`.
- Deduplicate aggressively. Reposts, pinned posts, and race conditions can produce repeated items.
- Preserve ordering by `create_time` descending unless the user asks for another order.

## Incremental sync mode

When previous exports exist:
1. load the existing highest `create_time`
2. crawl newer pages first
3. stop when you reach older already-known items repeatedly
4. merge without duplicates
5. keep a compact sync summary

### Subscription-aware behavior

If the creator was subscribed through the subscription manager:
- `backfill_all`: perform a full crawl on first sync, then use normal incremental sync later
- `latest_only`: set the lower bound to `subscription_started_at` on first sync and skip older history

This mode should be implemented by client-side filtering plus TikHub pagination. Do not assume TikHub provides a native new-post subscription callback.


## Output format

Return:
- creator resolved identity
- endpoint used
- page count
- item count
- whether crawl is complete
- export paths or inline sample
- recommended next step

## Hand-off rules

When the user wants creative takeaways, pass the exported dataset to the `douyin-shot-analysis-kb` skill.

## References to consult when needed

- `references/tikhub-douyin-harvest-notes.md`
- `references/normalized-video-schema.md`
- `scripts/normalize_videos.py`

## Example triggers

Use this skill when users say things like:
- 抓这个抖音号的全部视频
- 把这个博主所有短视频都拉下来
- 给我导出这个账号的发片历史
- 同步这个创作者最近所有作品
