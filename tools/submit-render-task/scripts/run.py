from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone
from common.storage import default_generated_video_dir, slugify
from common.runtime_registry import renders_registry_file, load_rows, save_rows
from common.volcengine_video import VolcengineVideoClient, VolcengineVideoError

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--request-json', required=True)
    parser.add_argument('--download-results', action='store_true')
    args = parser.parse_args()
    request_payload = json.loads(Path(args.request_json).read_text(encoding='utf-8'))
    creator_slug = slugify(request_payload.get('creator_slug') or 'unknown')
    client = VolcengineVideoClient()
    result = client.generate(request_payload)
    saved = []
    if args.download_results and result.get('result_urls'):
        saved = client.download_results(result['result_urls'], default_generated_video_dir(creator_slug))
    render_task_id = f"render_{uuid.uuid4().hex[:12]}"
    reg_file = renders_registry_file()
    rows = load_rows(reg_file)
    payload = {
        'render_task_id': render_task_id,
        'provider': 'volcengine_ark',
        'provider_task_id': result.get('task_id'),
        'status': 'success',
        'created_at': _now(),
        'request_json': request_payload,
        'response_json': result,
        'result_video_paths': saved,
    }
    rows.append(payload)
    save_rows(reg_file, rows)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
