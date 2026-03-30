from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from urllib.request import Request, urlopen
from urllib.parse import urlparse
from common.artifacts import register_artifact

def _download(url: str, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as resp:
        with open(path, 'wb') as f:
            shutil.copyfileobj(resp, f)
    return str(path)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--normalized-json', required=True)
    parser.add_argument('--output-dir', default='')
    args = parser.parse_args()
    row = json.loads(Path(args.normalized_json).read_text(encoding='utf-8'))
    output_dir = Path(args.output_dir) if args.output_dir else Path(args.normalized_json).resolve().parents[2] / 'downloads' / 'manual'
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = {}
    if row.get('play_url'):
        suffix = Path(urlparse(str(row['play_url'])).path).suffix or '.mp4'
        saved['video'] = _download(str(row['play_url']), output_dir / f"{row.get('video_id') or 'video'}{suffix}")
        register_artifact('local_video', saved['video'], creator_slug=row.get('author_unique_id') or row.get('author_name') or '', video_id=row.get('video_id') or '')
    print(json.dumps(saved, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
