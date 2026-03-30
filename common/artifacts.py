from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .storage import get_workspace_data_root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def registry_root() -> Path:
    root = get_workspace_data_root() / 'registry'
    root.mkdir(parents=True, exist_ok=True)
    return root


def artifacts_file() -> Path:
    return registry_root() / 'artifacts.jsonl'


def register_artifact(artifact_type: str, local_path: str, creator_slug: str = '', video_id: str = '', task_id: str = '', extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {
        'artifact_id': f"artifact_{uuid.uuid4().hex[:12]}",
        'artifact_type': artifact_type,
        'local_path': local_path,
        'creator_slug': creator_slug,
        'video_id': video_id,
        'task_id': task_id,
        'created_at': _now(),
        'extra': extra or {},
    }
    with artifacts_file().open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    return payload
