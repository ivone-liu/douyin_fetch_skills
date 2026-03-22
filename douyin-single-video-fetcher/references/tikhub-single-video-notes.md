# TikHub Single Video Notes

Use this skill for a single post only.

Typical endpoint families to prefer:
- fetch single video data
- fetch single video data V2
- fetch single video data V3 when field coverage or copyright handling is better
- fetch single video by sharing link when only a share link is available

Decision rule:
- if the user has `aweme_id`, prefer direct single-video lookup
- if the user has only a share link, resolve through the share-link endpoint first
- if the user later wants the creator history, switch to the full harvester skill instead of looping this skill manually
