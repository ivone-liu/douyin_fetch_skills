# Structured per-video analysis schema

Use this schema inside each markdown analysis file as a fenced `json` block under a heading such as `## Structured analysis JSON`.

```json
{
  "analysis_version": "1.0.0",
  "video": {
    "video_id": "string",
    "author_name": "string",
    "author_unique_id": "string",
    "create_time": "string|number|null",
    "duration_ms": 0,
    "desc": "string"
  },
  "analysis_scope": {
    "source_depth": "metadata_only|caption_plus_media_probe|video_probe_plus_keyframes|manual_review|llm_video_review",
    "confidence": "low|medium|high",
    "prerequisites_passed": true,
    "video_download_verified": true,
    "notes": ["string"]
  },
  "positioning": {
    "primary_goal": "engagement|conversion|awareness|trust|traffic|unknown",
    "secondary_goals": ["string"],
    "content_archetype": "educational|review|story|showcase|comparison|listicle|vlog|promo|unknown",
    "sub_archetypes": ["string"],
    "target_audience": "string"
  },
  "hook": {
    "hook_type": "question_hook|promise_hook|conflict_hook|direct_statement|story_hook|unknown",
    "hook_text": "string",
    "visual_hook": "string",
    "emotion": "string",
    "promise": "string",
    "time_range": "string"
  },
  "narrative": {
    "structure_formula": "string",
    "beats": [
      {
        "beat_id": 1,
        "beat_type": "hook|setup|conflict|proof|delivery|payoff|cta|other",
        "purpose": "string",
        "time_range": "string",
        "summary": "string",
        "proof_type": "demo|claim|story|comparison|testimonial|unknown"
      }
    ]
  },
  "shot_plan": {
    "dominant_style": "string",
    "shots": [
      {
        "shot_id": 1,
        "beat_id": 1,
        "time_range": "string",
        "shot_size": "ecu|cu|mcu|ms|mls|ls|ws|unknown",
        "camera_angle": "eye_level|high_angle|low_angle|pov|over_shoulder|unknown",
        "camera_movement": "static|push|pull|pan|tilt|track|handheld|unknown",
        "subject": "string",
        "scene_task": "string",
        "transition_in": "string",
        "transition_out": "string",
        "confidence": "low|medium|high"
      }
    ]
  },
  "dialogue": {
    "delivery_style": "string",
    "structure": "string",
    "rhetorical_moves": ["string"],
    "cta_type": "comment|follow|dm|save|profile_click|live_room|none|unknown"
  },
  "editing_packaging": {
    "pace": "fast|medium|slow|unknown",
    "subtitle_style": "full_subtitles|keyword_pop|hook_only|minimal|unknown",
    "transition_types": ["string"],
    "packaging_elements": ["string"],
    "audio_strategy": "string"
  },
  "persuasion": {
    "emotion_triggers": ["string"],
    "credibility_signals": ["string"],
    "conversion_devices": ["string"]
  },
  "reusable_patterns": {
    "opening_formula": "string",
    "structure_formula": "string",
    "shot_formula": "string",
    "dialogue_formula": "string",
    "applicable_scenarios": ["string"],
    "not_applicable_scenarios": ["string"]
  },
  "risks_and_limits": {
    "risk_flags": ["string"],
    "unknowns": ["string"]
  },
  "evidence": {
    "local_video_path": "string",
    "media_profile": {},
    "scene_info": {},
    "editing_metrics": {},
    "engagement_profile": {},
    "copy_profile": {},
    "contact_sheet_path": "string|null",
    "keyframe_paths": ["string"]
  }
}
```

Rules:
- keep every section even when fields are `unknown`
- never invent shot-level certainty from metadata only
- do not generate the analysis markdown at all before local video download succeeds
- if analysis is only a scaffold, say so in `analysis_scope.notes`
- downstream KB building should prefer rows where `analysis_scope.prerequisites_passed=true` and `source_depth` is beyond metadata-only
