from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.storage import get_workspace_data_root
from common.runtime_registry import scripts_registry_file, renders_registry_file, load_rows

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--entity', required=True, choices=['creators', 'tasks', 'artifacts', 'scripts', 'renders'])
    args = parser.parse_args()
    root = get_workspace_data_root()
    if args.entity == 'creators':
        rows = [p.name for p in sorted((root / 'creators').glob('*')) if p.is_dir()]
        print(json.dumps({'entity': 'creators', 'items': rows}, ensure_ascii=False, indent=2))
        return 0
    if args.entity == 'tasks':
        rows = []
        for p in sorted((root / 'tasks').glob('*/task.json')):
            rows.append(json.loads(p.read_text(encoding='utf-8')))
        print(json.dumps({'entity': 'tasks', 'items': rows}, ensure_ascii=False, indent=2))
        return 0
    if args.entity == 'artifacts':
        path = root / 'registry' / 'artifacts.jsonl'
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
        print(json.dumps({'entity': 'artifacts', 'items': rows}, ensure_ascii=False, indent=2))
        return 0
    if args.entity == 'scripts':
        path = scripts_registry_file()
        rows = load_rows(path)
        print(json.dumps({'entity': 'scripts', 'items': rows}, ensure_ascii=False, indent=2))
        return 0
    if args.entity == 'renders':
        path = renders_registry_file()
        rows = load_rows(path)
        print(json.dumps({'entity': 'renders', 'items': rows}, ensure_ascii=False, indent=2))
        return 0
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
