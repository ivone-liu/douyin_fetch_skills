# Script schema

```json
{
  "idea": {
    "topic_angle": "string",
    "audience": "string",
    "goal": "string"
  },
  "hook": {
    "line": "string",
    "visual": "string",
    "source_patterns": ["pattern_id"]
  },
  "beats": [
    {
      "beat": 1,
      "purpose": "setup|conflict|proof|payoff|cta",
      "script": "string",
      "suggested_shot": "string",
      "on_screen_text": "string"
    }
  ],
  "cta": "string",
  "fit_notes": ["string"],
  "risk_notes": ["string"]
}
```
