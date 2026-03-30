from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.storage import default_generated_video_dir
from common.runtime_registry import renders_registry_file, load_rows, save_rows
from common.volcengine_video import VolcengineVideoClient

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--render-task-id', required=True)
    parser.add_argument('--notes', default='')
    args = parser.parse_args()
    reg_file = renders_registry_file()
    if not reg_file.exists():
        raise SystemExit('未找到渲染登记表')
    rows = load_rows(reg_file)
    row = next((r for r in rows if r.get('render_task_id') == args.render_task_id), None)
    if row is None:
        raise SystemExit('Render task not found')
    request_payload = dict(row.get('request_json') or {})
    if args.notes:
        request_payload['prompt'] = f"{request_payload.get('prompt', '')}\n附加修改要求：{args.notes}".strip()
    client = VolcengineVideoClient()
    result = client.generate(request_payload)
    saved = client.download_results(result.get('result_urls') or [], default_generated_video_dir(request_payload.get('creator_slug') or 'unknown')) if result.get('result_urls') else []
    new_row = {
        'render_task_id': f"render_{uuid.uuid4().hex[:12]}",
        'provider': 'volcengine_ark',
        'provider_task_id': result.get('task_id'),
        'status': 'success',
        'request_json': request_payload,
        'response_json': result,
        'result_video_paths': saved,
        'parent_render_task_id': args.render_task_id,
    }
    rows.append(new_row)
    save_rows(reg_file, rows)
    print(json.dumps(new_row, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
