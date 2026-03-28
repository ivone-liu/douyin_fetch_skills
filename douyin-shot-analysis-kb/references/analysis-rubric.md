# Analysis rubric

## Evidence hierarchy

Strongest to weakest:
1. frame-level or transcript-backed direct video observation
2. subtitle, ASR, or sampled-frame review
3. normalized metadata with engagement metrics
4. caption-only inference

Always record which evidence level the analysis used.
Do not let a low-evidence analysis masquerade as a deep structural read.

## Required dimensions for every single-video analysis

Every per-video analysis must try to cover these layers:
- objective and commercial intent
- content archetype
- hook design
- narrative beats
- shot list or shot-language summary
- dialogue and rhetorical moves
- editing and packaging
- persuasion devices
- reusable pattern abstraction
- uncertainty and missing evidence

If a layer cannot be observed with confidence, keep the field but mark it `unknown` or `needs_manual_review`.
Do not silently omit the layer.

## Required dimensions for creator-level KBs

Every creator-level KB should summarize repeated patterns across:
- primary goals
- content archetypes
- hooks
- beat structures
- shot language
- dialogue tactics
- editing rhythm and packaging
- persuasion and CTA patterns
- anti-patterns and limits

## Rule for conclusions

Do not write claims that cannot be traced back to one of these:
- repeated pattern across multiple videos
- outlier post with explicit evidence video ids
- metric association visible in the dataset
- a single-video observation clearly marked as non-generalizable

## Rule for reuse

Each conclusion should end in one of these forms:
- do this
- test this
- avoid this
- use only when these conditions are true
- do not transfer this outside the original persona or production setup

## Confidence rules

- `high`: frame-level, transcript, or manually verified analysis with concrete beat or shot evidence
- `medium`: multiple aligned signals from caption, metadata, and media probes, but not full direct observation
- `low`: metadata-only, caption-only, or sparse observations

Confidence is about evidence depth, not about how convincing the prose sounds.
