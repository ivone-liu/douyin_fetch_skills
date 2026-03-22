#!/usr/bin/env python3
"""Build a lightweight creator KB from local markdown analysis documents.

Usage:
python scripts/build_kb_from_md.py ../data/creators/creator-slug/analysis_md ./kb/creator-slug
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def parse_md(path: Path) -> dict:
    text = path.read_text(encoding='utf-8')
    data = {'video_id': path.stem, 'path': str(path), 'hook_type': None, 'script_structure': None}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('- hook_type:'):
            data['hook_type'] = line.split(':', 1)[1].strip()
        elif line.startswith('- script_structure:'):
            data['script_structure'] = line.split(':', 1)[1].strip()
    return data


def main() -> int:
    if len(sys.argv) != 3:
        print('Usage: build_kb_from_md.py md_dir output_dir', file=sys.stderr)
        return 2
    md_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    rows = [parse_md(p) for p in sorted(md_dir.rglob('*.md'))]
    hooks = Counter(r['hook_type'] for r in rows if r.get('hook_type'))
    structures = Counter(r['script_structure'] for r in rows if r.get('script_structure'))
    kb = {
        'built_at': datetime.now(timezone.utc).isoformat(),
        'source_type': 'local_markdown',
        'video_count': len(rows),
        'top_hooks': hooks.most_common(10),
        'top_structures': structures.most_common(10),
        'videos': rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'knowledge-base.json').write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding='utf-8')
    md_lines = ['# Markdown-derived KB', '', f'- video_count: {len(rows)}', '', '## Top hooks']
    for value, count in hooks.most_common(10):
        md_lines.append(f'- {value}: {count}')
    md_lines.append('')
    md_lines.append('## Top structures')
    for value, count in structures.most_common(10):
        md_lines.append(f'- {value}: {count}')
    (out_dir / 'knowledge-base.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')
    print(f'Wrote markdown-derived KB to {out_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
