from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .storage import get_workspace_data_root


def registry_root() -> Path:
    root = get_workspace_data_root() / 'registry'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _json_file(name: str) -> Path:
    path = registry_root() / name
    if not path.exists():
        path.write_text('[]', encoding='utf-8')
    return path


def scripts_registry_file() -> Path:
    return _json_file('scripts.json')


def renders_registry_file() -> Path:
    return _json_file('renders.json')


def load_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8'))


def save_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
