#!/usr/bin/env python3
"""Read one or more local markdown analysis files and return a compact combined view.

Example:
python scripts/read_local_md.py ~/.openclaw/workspace/~/.openclaw/workspace/data/creators/creator-slug/analysis_md
python scripts/read_local_md.py ~/.openclaw/workspace/~/.openclaw/workspace/data/creators/creator-slug/analysis_md/1234567890.md
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def extract_structured_json(text: str) -> dict:
    for match in JSON_BLOCK_RE.finditer(text):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and (data.get('analysis_version') or data.get('video') or data.get('positioning')):
            return data
    return {}


def read_md(path: Path) -> dict:
    text = path.read_text(encoding='utf-8')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    structured = extract_structured_json(text)
    title = lines[0].lstrip('# ').strip() if lines else path.stem
    meta = {
        'path': str(path),
        'title': title,
        'video_id': path.stem,
        'hook_type': None,
        'script_structure': None,
        'structured': structured,
    }
    if structured:
        video = structured.get('video') or {}
        meta['video_id'] = video.get('video_id') or path.stem
        meta['hook_type'] = ((structured.get('hook') or {}).get('hook_type'))
        meta['script_structure'] = ((structured.get('narrative') or {}).get('structure_formula'))
    else:
        for line in lines:
            if line.startswith('- hook_type:'):
                meta['hook_type'] = line.split(':', 1)[1].strip()
            elif line.startswith('- script_structure:'):
                meta['script_structure'] = line.split(':', 1)[1].strip()
    meta['excerpt'] = '\n'.join(lines[:24])
    return meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    args = parser.parse_args()
    target = Path(args.target)
    files = [target] if target.is_file() else sorted(target.rglob('*.md'))
    rows = [read_md(p) for p in files]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
