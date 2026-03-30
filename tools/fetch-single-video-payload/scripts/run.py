from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.tikhub import TikHubClient

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', help='Share link, share text, URL, or aweme_id')
    parser.add_argument('--input-json', help='Use an existing payload instead of calling TikHub')
    parser.add_argument('--output', required=True)
    parser.add_argument('--need-anchor-info', action='store_true')
    args = parser.parse_args()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.input_json:
        payload = json.loads(Path(args.input_json).read_text(encoding='utf-8'))
    else:
        if not args.source:
            raise SystemExit('Either --source or --input-json is required')
        client = TikHubClient()
        source = args.source.strip()
        if source.isdigit():
            payload = client.fetch_video_by_aweme_id(source, need_anchor_info=args.need_anchor_info)
        else:
            payload = client.fetch_video_by_url(source)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out_path), 'keys': list(payload.keys())[:20]}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
