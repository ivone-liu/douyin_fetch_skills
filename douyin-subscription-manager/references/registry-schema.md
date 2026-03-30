# Subscription registry schema

Suggested JSON shape:

```json
{
  "creators": [
    {
      "creator_key": "sec_user_id_or_unique_id",
      "display_name": "string",
      "sec_user_id": "string",
      "unique_id": "string",
      "uid": "string",
      "status": "subscribed",
      "source": "manual",
      "created_at": "2026-03-20T00:00:00Z",
      "updated_at": "2026-03-20T00:00:00Z",
      "notes": "optional"
    }
  ]
}
```

Rules:
- `creator_key` must be stable and unique.
- Prefer `sec_user_id` over `unique_id` when both exist.
- Preserve prior identifiers when a newer sync returns fewer fields.
