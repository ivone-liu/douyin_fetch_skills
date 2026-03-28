from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

DEFAULT_WORKSPACE_DATA_ROOT = Path('~/.openclaw/workspace/data').expanduser()


def get_workspace_data_root() -> Path:
    raw = (
        os.getenv('OPENCLAW_WORKSPACE_DATA_ROOT')
        or os.getenv('OPENCLAW_DATA_ROOT')
        or str(DEFAULT_WORKSPACE_DATA_ROOT)
    )
    root = Path(raw).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_creators_root() -> Path:
    root = get_workspace_data_root() / 'creators'
    root.mkdir(parents=True, exist_ok=True)
    return root


def slugify(value: str) -> str:
    value = (value or 'unknown').strip().lower()
    value = re.sub(r'[^a-z0-9一-鿿_-]+', '-', value)
    value = re.sub(r'-+', '-', value).strip('-')
    return value or 'unknown'


def creator_root(creator_slug: str) -> Path:
    root = get_creators_root() / slugify(creator_slug)
    root.mkdir(parents=True, exist_ok=True)
    return root


def detect_creator_slug_from_path(path: Path) -> Optional[str]:
    parts = list(path.expanduser().resolve().parts)
    if 'creators' not in parts:
        return None
    idx = parts.index('creators')
    if idx + 1 >= len(parts):
        return None
    return parts[idx + 1]


def default_kb_dir_for_analysis_md(md_dir: Path) -> Path:
    slug = detect_creator_slug_from_path(md_dir)
    if slug:
        return creator_root(slug) / 'kb'
    return md_dir.parent / 'kb'


def default_generated_script_dir(creator_slug: str) -> Path:
    out = creator_root(creator_slug) / 'generated_scripts'
    out.mkdir(parents=True, exist_ok=True)
    return out


def default_generated_video_dir(creator_slug: str) -> Path:
    out = creator_root(creator_slug) / 'generated_videos'
    out.mkdir(parents=True, exist_ok=True)
    return out
