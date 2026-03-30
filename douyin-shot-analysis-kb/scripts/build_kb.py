#!/usr/bin/env python3
"""Compatibility entrypoint for building a creator KB.

Preferred mode:
python scripts/build_kb.py ~/.openclaw/workspace/data/creators/<creator-slug>/analysis_md

Fallback mode:
python scripts/build_kb.py normalized_videos.json [output_dir]
This mode creates a minimal manifest but does not index into Qdrant unless markdown analyses exist.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PACK_ROOT = Path(__file__).resolve().parents[2]
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from common.haystack_rag import collection_name_for_creator
from common.storage import creator_root, detect_creator_slug_from_path, slugify
from build_kb_from_md import main as build_from_md_main


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def timestamp_range(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    vals = [str(x.get('create_time')) for x in items if x.get('create_time') is not None]
    if not vals:
        return {'earliest': None, 'latest': None}
    return {'earliest': min(vals), 'latest': max(vals)}


def fallback_manifest(videos: List[Dict[str, Any]], output_dir: Path) -> Dict[str, Any]:
    first = videos[0] if videos else {}
    creator_slug = slugify(first.get('author_unique_id') or first.get('author_name') or 'unknown-creator')
    manifest = {
        'kb_version': 'haystack_qdrant_v1',
        'creator_slug': creator_slug,
        'qdrant': {
            'url': 'http://127.0.0.1:6333',
            'collection_name': collection_name_for_creator(creator_slug),
            'embedding_backend': 'not_indexed',
            'embedding_model': None,
            'embedding_dim': None,
        },
        'dataset': {
            'video_count': len(videos),
            'chunk_count': 0,
            'indexed_at': datetime.now(timezone.utc).isoformat(),
            'confidence': 'low',
            'note': 'No markdown analyses were provided, so no Haystack/Qdrant indexing was performed.',
            'time_range': timestamp_range(videos),
        },
        'videos': [
            {
                'video_id': str(v.get('video_id') or v.get('aweme_id') or 'unknown-video'),
                'primary_goal': 'unknown',
                'content_archetype': 'unknown',
                'hook_type': 'unknown',
                'source_path': '',
                'doc_count': 0,
            }
            for v in videos
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'knowledge-base.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (output_dir / 'knowledge-base.md').write_text(
        '# Metadata-only KB\n\nNo markdown analyses were available, so no Qdrant index was built.\n',
        encoding='utf-8',
    )
    (output_dir / 'video-index.json').write_text(json.dumps(manifest['videos'], ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: build_kb.py analysis_md_dir | normalized_videos.json [output_dir]', file=sys.stderr)
        return 2
    first_arg = Path(sys.argv[1]).expanduser().resolve()
    if first_arg.is_dir():
        sys.argv = [sys.argv[0], str(first_arg), *(sys.argv[2:])]
        return build_from_md_main()

    normalized_path = first_arg
    output_dir = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) >= 3 else None
    videos = load_json(normalized_path)
    if not isinstance(videos, list):
        videos = videos.get('items') or []
    if output_dir is None:
        slug = detect_creator_slug_from_path(normalized_path) or slugify((videos[0] if videos else {}).get('author_unique_id') or (videos[0] if videos else {}).get('author_name') or 'unknown-creator')
        output_dir = creator_root(str(slug)) / 'kb'
    manifest = fallback_manifest(videos, output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
