#!/usr/bin/env python3
"""Build a creator RAG knowledge base from markdown analyses using Haystack + Qdrant.

Usage:
python scripts/build_kb_from_md.py ~/.openclaw/workspace/data/creators/<creator-slug>/analysis_md
python scripts/build_kb_from_md.py ~/.openclaw/workspace/data/creators/<creator-slug>/analysis_md ~/.openclaw/workspace/data/creators/<creator-slug>/kb --append
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2]
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from common.haystack_rag import RagConfig, index_analysis_dir_to_qdrant
from common.storage import default_kb_dir_for_analysis_md


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('analysis_md_dir')
    parser.add_argument('output_dir', nargs='?')
    parser.add_argument('--append', action='store_true', help='Append to the existing Qdrant collection instead of recreating it.')
    args = parser.parse_args()

    analysis_dir = Path(args.analysis_md_dir).expanduser().resolve()
    if not analysis_dir.exists():
        raise SystemExit(f'analysis_md dir not found: {analysis_dir}')
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_kb_dir_for_analysis_md(analysis_dir)
    manifest = index_analysis_dir_to_qdrant(analysis_dir, output_dir, recreate=not args.append, config=RagConfig())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
