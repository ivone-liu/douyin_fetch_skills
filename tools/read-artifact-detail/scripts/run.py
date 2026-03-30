from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True)
    args = parser.parse_args()
    path = Path(args.path).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f'Artifact not found: {path}')
    if path.suffix.lower() in {'.json', '.jsonl', '.md', '.txt'}:
        print(path.read_text(encoding='utf-8', errors='ignore'))
    else:
        print(json.dumps({'path': str(path), 'size': path.stat().st_size, 'suffix': path.suffix}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
