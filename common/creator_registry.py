from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .storage import get_workspace_data_root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def registry_file() -> Path:
    path = get_workspace_data_root() / 'registry' / 'subscriptions.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text('[]', encoding='utf-8')
    return path


def load_subscriptions() -> List[Dict[str, Any]]:
    return json.loads(registry_file().read_text(encoding='utf-8'))


def save_subscriptions(rows: List[Dict[str, Any]]) -> None:
    registry_file().write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


def upsert_subscription(row: Dict[str, Any]) -> Dict[str, Any]:
    rows = load_subscriptions()
    key = row.get('creator_key') or row.get('sec_user_id') or row.get('unique_id')
    found = None
    for existing in rows:
        existing_key = existing.get('creator_key') or existing.get('sec_user_id') or existing.get('unique_id')
        if existing_key and existing_key == key:
            found = existing
            break
    if found is None:
        row.setdefault('created_at', _now())
        row['updated_at'] = _now()
        rows.append(row)
        save_subscriptions(rows)
        return row
    found.update(row)
    found['updated_at'] = _now()
    save_subscriptions(rows)
    return found
