# TikHub Douyin subscription notes

## What the public docs confirm

TikHub documents a Douyin interaction area that includes actions such as like, follow, collect, and forward. The README index lists `关注/Follow` under the Douyin interaction section, which confirms that a follow capability exists in the platform docs.

TikHub also documents multiple Douyin profile and relationship endpoints, including user profile lookups and following list retrieval.

## Practical implementation guidance

Use this resolution chain before any follow or unfollow call:
1. profile by `sec_user_id`
2. profile by `unique_id`
3. extract ids from share link
4. search fallback

Use following list retrieval to verify final state when the user asks for confirmation.

## Endpoint naming caveat

TikHub public indexes expose the capability names clearly, but some leaf pages are unstable to fetch automatically. Validate the exact request path in your own TikHub workspace before production rollout.

## Recommended secrets

- `TIKHUB_API_TOKEN`
- `TIKHUB_BASE_URL`, default `https://api.tikhub.io`
- account cookies or device tokens if your chosen TikHub follow flow requires them
