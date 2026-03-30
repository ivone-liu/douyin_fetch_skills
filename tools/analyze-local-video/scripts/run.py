from __future__ import annotations
import argparse, json, os, sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.tasks import create_task, update_task, append_step

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--normalized-json', default='')
    parser.add_argument('--video', default='')
    parser.add_argument('--creator-slug', default='')
    parser.add_argument('--video-id', default='')
    parser.add_argument('--desc', default='')
    parser.add_argument('--stats-json', default='')
    parser.add_argument('--mysql-dsn', default=os.getenv('MYSQL_DSN', ''))
    args = parser.parse_args()

    if not args.normalized_json and not args.video:
        parser.error('必须提供 --normalized-json 或 --video')
    if args.video and not args.creator_slug:
        parser.error('使用 --video 时必须同时提供 --creator-slug')

    entity_id = args.video_id or args.normalized_json or args.video
    task = create_task('analyze_local_video', entity_type='video', entity_id=entity_id, input_json=vars(args))
    update_task(task['task_id'], status='running', current_stage='analyze_local_video')
    script = ROOT / 'scripts' / 'analyze_local_video.py'
    if args.normalized_json:
        cmd = [sys.executable, str(script), args.normalized_json]
    else:
        # backward-compatible shim: synthesize a temporary normalized payload file next to the video
        tmp_dir = Path(os.getenv('OPENCLAW_WORKSPACE_DATA_ROOT', Path.home()/'.openclaw/workspace/data')).expanduser()/ 'tmp'
        tmp_dir.mkdir(parents=True, exist_ok=True)
        normalized_path = tmp_dir / f"analyze_{(args.video_id or Path(args.video).stem)}.json"
        normalized_path.write_text(json.dumps({
            'video_id': args.video_id or Path(args.video).stem,
            'author_unique_id': args.creator_slug,
            'author_name': args.creator_slug,
            'desc': args.desc or '',
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        cmd = [sys.executable, str(script), str(normalized_path)]
    env = os.environ.copy()
    if args.mysql_dsn:
        env['MYSQL_DSN'] = args.mysql_dsn
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    append_step(task['task_id'], 'analyze_local_video', 'success' if proc.returncode == 0 else 'failed', input_ref={'normalized_json': args.normalized_json, 'video': args.video}, output_ref={'stdout': proc.stdout[-4000:]}, error_message=proc.stderr[-4000:])
    if proc.returncode != 0:
        update_task(task['task_id'], status='failed', error_message=(proc.stderr or proc.stdout)[-2000:])
        sys.stderr.write(proc.stderr or proc.stdout)
        return proc.returncode
    update_task(task['task_id'], status='success', current_stage='done')
    sys.stdout.write(proc.stdout)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
