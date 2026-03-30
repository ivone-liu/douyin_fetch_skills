from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .storage import get_workspace_data_root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tasks_root() -> Path:
    root = get_workspace_data_root() / 'tasks'
    root.mkdir(parents=True, exist_ok=True)
    return root


def task_dir(task_id: str) -> Path:
    path = tasks_root() / task_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_task(task_type: str, entity_type: str = '', entity_id: str = '', input_json: Optional[Dict[str, Any]] = None, parent_task_id: str = '') -> Dict[str, Any]:
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    payload = {
        'task_id': task_id,
        'task_type': task_type,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'parent_task_id': parent_task_id,
        'status': 'pending',
        'current_stage': '',
        'input_json': input_json or {},
        'output_json': {},
        'created_at': _now(),
        'started_at': '',
        'finished_at': '',
        'error_message': '',
    }
    write_task(payload)
    return payload


def task_file(task_id: str) -> Path:
    return task_dir(task_id) / 'task.json'


def steps_file(task_id: str) -> Path:
    return task_dir(task_id) / 'steps.jsonl'


def read_task(task_id: str) -> Dict[str, Any]:
    return json.loads(task_file(task_id).read_text(encoding='utf-8'))


def write_task(payload: Dict[str, Any]) -> Path:
    path = task_file(payload['task_id'])
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def update_task(task_id: str, **patch: Any) -> Dict[str, Any]:
    payload = read_task(task_id)
    payload.update(patch)
    if patch.get('status') == 'running' and not payload.get('started_at'):
        payload['started_at'] = _now()
    if patch.get('status') in {'success', 'failed', 'cancelled', 'partial_success'}:
        payload['finished_at'] = _now()
    write_task(payload)
    return payload


def append_step(task_id: str, step_name: str, status: str, input_ref: Any = None, output_ref: Any = None, error_message: str = '') -> Dict[str, Any]:
    rec = {
        'time': _now(),
        'task_id': task_id,
        'step_name': step_name,
        'status': status,
        'input_ref': input_ref,
        'output_ref': output_ref,
        'error_message': error_message,
    }
    path = steps_file(task_id)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return rec
