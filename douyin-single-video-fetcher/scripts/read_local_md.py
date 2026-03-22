#!/usr/bin/env python3
"""Read one or more local markdown analysis files and return a compact combined view.

Example:
python scripts/read_local_md.py ./storage/analysis_md/creator-slug
python scripts/read_local_md.py ./storage/analysis_md/creator-slug/1234567890.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_md(path: Path) -> dict:
    text = path.read_text(encoding='utf-8')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    meta = {
        'path': str(path),
        'title': lines[0].lstrip('# ').strip() if lines else path.stem,
        'hook_type': None,
        'script_structure': None,
    }
    for line in lines:
        if line.startswith('- hook_type:'):
            meta['hook_type'] = line.split(':', 1)[1].strip()
        elif line.startswith('- script_structure:'):
            meta['script_structure'] = line.split(':', 1)[1].strip()
    meta['excerpt'] = '\n'.join(lines[:20])
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
