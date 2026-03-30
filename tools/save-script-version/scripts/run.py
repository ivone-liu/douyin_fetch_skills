from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone
from common.storage import creator_root
from common.runtime_registry import scripts_registry_file, load_rows, save_rows

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--creator-slug', required=True)
    parser.add_argument('--mode', required=True)
    parser.add_argument('--topic', default='')
    parser.add_argument('--source-json', default='')
    parser.add_argument('--source-md', default='')
    parser.add_argument('--parent-script-id', default='')
    args = parser.parse_args()
    creator_dir = creator_root(args.creator_slug) / 'generated_scripts'
    creator_dir.mkdir(parents=True, exist_ok=True)
    script_id = f"script_{uuid.uuid4().hex[:12]}"
    target_dir = creator_dir / script_id
    target_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'script_id': script_id,
        'parent_script_id': args.parent_script_id,
        'creator_slug': args.creator_slug,
        'mode': args.mode,
        'topic': args.topic,
        'created_at': _now(),
    }
    if args.source_json:
        shutil.copy2(args.source_json, target_dir / 'script.json')
        payload['content_json_path'] = str(target_dir / 'script.json')
    if args.source_md:
        shutil.copy2(args.source_md, target_dir / 'script.md')
        payload['content_md_path'] = str(target_dir / 'script.md')
    reg_file = scripts_registry_file()
    rows = load_rows(reg_file)
    rows.append(payload)
    save_rows(reg_file, rows)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
