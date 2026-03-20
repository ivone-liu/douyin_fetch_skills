# TikHub Douyin harvest notes

## What the public docs confirm

TikHub's README index for Douyin web lists these relevant capabilities:
- get single video data
- get user homepage video data
- get user like video data
- get user collection data
- get user mix video data
- get user profile by several identifiers
- get highest quality play URL of the video
- batch get highest quality play URL of videos

This confirms that TikHub supports the full chain needed for creator backfill: identity resolution, paginated post retrieval, and playback enrichment.

## Known pagination pattern

The public search snippet for the homepage-video page states that the request uses:
- `sec_user_id`
- `max_cursor`
- `count`

and that the first page uses `max_cursor = 0`.

## Endpoint naming caveat

The capability names are confirmed by the docs index, but the exact leaf page paths can be brittle. Verify the final request path and request method inside your own TikHub console before deployment.

## Recommended crawl policy

- default `count = 20`
- retry up to 3 times on 429 or transient 5xx
- save partial result after repeated failures
- enrich play URLs only when needed
