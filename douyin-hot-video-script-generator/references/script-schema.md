# Script schema

```json
{
  "idea": {
    "topic_angle": "string",
    "audience": "string",
    "goal": "string",
    "duration_target_sec": 30,
    "constraints": ["string"]
  },
  "positioning": {
    "content_archetype": "string",
    "delivery_style": "string",
    "evidence_patterns": ["pattern_id"]
  },
  "hook": {
    "line": "string",
    "visual": "string",
    "source_patterns": ["pattern_id"]
  },
  "beats": [
    {
      "beat": 1,
      "purpose": "hook|setup|conflict|proof|delivery|payoff|cta",
      "script": "string",
      "suggested_shot": "string",
      "on_screen_text": "string",
      "dialogue_move": "string"
    }
  ],
  "shot_plan": [
    {
      "shot_id": 1,
      "purpose": "string",
      "shot_hint": "string",
      "movement_hint": "string",
      "transition_hint": "string"
    }
  ],
  "cta": "string",
  "fit_notes": ["string"],
  "risk_notes": ["string"]
}
```
