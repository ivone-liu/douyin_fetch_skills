---
name: douyin-subscription-manager
description: Manage Douyin account subscriptions through TikHub. Use when the user asks to subscribe to a Douyin creator, unsubscribe from one, check whether an account is already subscribed, sync a local subscription list with TikHub, or maintain a watchlist of creators for later crawling.
compatibility: Works best in environments with TikHub API access, outbound network access, secure secret storage for TIKHUB_API_TOKEN, and a writable local file system for a subscription registry.
metadata:
  author: OpenAI
  version: 1.0.0
  category: workflow-automation
  upstream: tikhub-douyin
---

# Douyin Subscription Manager

This skill manages creator subscriptions for downstream crawling and analysis workflows.

Use this skill when the user wants any of the following:
- subscribe to a Douyin creator
- unsubscribe from a Douyin creator
- verify whether a creator is already tracked
- keep a canonical creator registry for later batch crawling
- normalize creator identifiers before other Douyin workflows run

## What this skill is responsible for

This skill is the control layer for creator tracking. It should:
1. resolve the creator identity into a stable identifier
2. decide whether the action is add, remove, list, or verify
3. execute the TikHub interaction only when credentials and required identifiers are present
4. update the local subscription registry after a successful remote action
5. return a compact, auditable result

This skill should not crawl all videos or analyze creative techniques. Hand those tasks to the dedicated skills.

## Required inputs

Try to obtain, in this order:
1. `sec_user_id`
2. `unique_id` which is the Douyin handle
3. share link
4. profile URL
5. plain creator name, only as a last resort because names are ambiguous

If the user gives only a fuzzy creator name, first resolve identity before attempting any follow or unfollow action.

## Workflow

### A. Determine the requested operation
Classify the request as one of:
- subscribe
- unsubscribe
- list
- verify
- sync-local-registry

If the request mixes operations, execute them in a safe order:
1. resolve identities
2. validate identifiers
3. perform remote mutations
4. update local registry
5. report final state

### B. Resolve creator identity
Use TikHub Douyin profile endpoints to normalize the target account.
Preferred resolution order:
1. get user by `sec_user_id`
2. get user by `unique_id`
3. extract ids from share link, then fetch profile
4. search as a fallback only when exact ids are unavailable

Store these fields whenever available:
- display_name
- sec_user_id
- unique_id
- uid
- short_id
- profile_url
- avatar_url
- follower_count
- following_count

If multiple accounts match and the identity is ambiguous, stop and present a concise disambiguation list instead of guessing.

### C. Perform the action
For subscribe and unsubscribe:
- verify TikHub credentials are available
- verify the target account has a stable identifier
- call the documented TikHub follow or unfollow capability for Douyin interactions
- treat a duplicate subscribe as idempotent success
- treat a missing subscription on unsubscribe as idempotent success

For list and verify:
- prefer the local registry when it exists and is fresh
- use TikHub following endpoints when the user explicitly asks for remote truth
- surface mismatches between local and remote state

### D. Update the local registry
Maintain a registry file named `subscriptions.json` if the environment supports local storage.
Each item should contain:
- `creator_key`, derived from `sec_user_id` when available, else `unique_id`
- `display_name`
- `sec_user_id`
- `unique_id`
- `uid`
- `status`, either `subscribed` or `unsubscribed`
- `source`, such as manual, imported, or synced
- `created_at`
- `updated_at`
- `notes`

Never overwrite a creator record with poorer identity data. Prefer the most stable identifiers.

## Safety and validation rules

- Do not subscribe or unsubscribe an ambiguous account.
- Do not assume display names are unique.
- Do not silently ignore remote API failures.
- If the remote action fails but the local registry was updated, roll back the local change or clearly mark the record as `pending_sync`.
- If TikHub credentials are missing, provide the exact missing variables and stop.
- If the user asks to bulk subscribe by spreadsheet or long list, process in batches and report per item status.

## Output format

Return a concise operational report with:
- requested action
- resolved creator identity
- remote action result
- local registry result
- next recommended step

For bulk actions, use this structure for each creator:
- creator
- action
- remote_status
- local_status
- notes

## Hand-off rules

After a successful subscribe, suggest the video crawling skill when the user wants all posts.
After crawling is complete, suggest the analysis skill when the user wants a reusable knowledge base.

## Recommended local file layout

If file storage is available, use:
- `data/subscriptions.json`
- `data/subscription-audit.log`

## References to consult when needed

Before implementing or debugging, check:
- `references/tikhub-douyin-subscription-notes.md`
- `references/registry-schema.md`

## Example triggers

Use this skill when users say things like:
- 帮我订阅这个抖音号
- 把这个账号加到追踪列表
- 取消订阅这个创作者
- 看看我有没有订阅这个博主
- 把这些抖音账号都加入监控名单
