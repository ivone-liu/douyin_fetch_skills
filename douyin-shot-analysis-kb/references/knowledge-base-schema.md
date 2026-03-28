# Knowledge base schema

Suggested `knowledge-base.json` shape:

```json
{
  "creator": {
    "creator_key": "sec_user_id_or_unique_id",
    "display_name": "string",
    "sec_user_id": "string",
    "unique_id": "string"
  },
  "dataset": {
    "video_count": 0,
    "analysis_count": 0,
    "time_range": {
      "earliest": "ISO datetime or unix timestamp string",
      "latest": "ISO datetime or unix timestamp string"
    },
    "built_at": "2026-03-20T00:00:00Z",
    "confidence": "low|medium|high",
    "source_breakdown": {
      "metadata_only": 0,
      "manual_or_model_review": 0
    }
  },
  "pattern_groups": {
    "goals": [],
    "archetypes": [],
    "hooks": [],
    "beats": [],
    "shots": [],
    "dialogue": [],
    "editing": [],
    "persuasion": [],
    "cta": [],
    "reusable_formulas": [],
    "risks": []
  },
  "patterns": [
    {
      "pattern_id": "hook_type_001",
      "category": "hook_type",
      "summary": "问题句 + 结果承诺开头",
      "evidence_video_ids": ["123", "456"],
      "confidence": 0.78,
      "reusability_note": "适用于知识分享和教程内容",
      "when_to_use": "需要快速抓住痛点时",
      "when_not_to_use": "强调氛围感而非信息密度时",
      "evidence_count": 2,
      "sample_details": [
        {
          "video_id": "123",
          "detail": "开头直接指出误区"
        }
      ]
    }
  ],
  "video_index": [
    {
      "video_id": "123",
      "primary_goal": "engagement",
      "content_archetype": "educational",
      "hook_type": "question_hook",
      "structure_formula": "problem -> explanation -> action -> cta",
      "source_depth": "metadata_only",
      "confidence": "low"
    }
  ],
  "playbook": {
    "do_this": ["string"],
    "test_this": ["string"],
    "avoid_this": ["string"]
  }
}
```

Rules:
- every pattern must keep evidence video ids
- `confidence` must reflect data depth, not optimism
- `pattern_groups` are curated views over `patterns`, not a second independent truth source
- `video_index` should remain compact but queryable
- `playbook` is derivative, not raw evidence
