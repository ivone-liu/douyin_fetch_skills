from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from urllib.parse import urlparse

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    src = args.source.strip()
    out = {'source': src, 'source_type': 'unknown', 'normalized_value': src, 'aweme_id': ''}
    if Path(src).exists():
        out['source_type'] = 'local_file'
    elif src.startswith('http://') or src.startswith('https://'):
        out['source_type'] = 'url'
        parsed = urlparse(src)
        out['normalized_value'] = parsed.geturl()
    elif src.isdigit():
        out['source_type'] = 'aweme_id'
        out['aweme_id'] = src
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
