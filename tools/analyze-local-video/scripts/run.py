from __future__ import annotations
import argparse, os, sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.tasks import create_task, update_task, append_step

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', required=True)
    parser.add_argument('--creator-slug', required=True)
    parser.add_argument('--video-id', default='')
    parser.add_argument('--desc', default='')
    parser.add_argument('--stats-json', default='')
    parser.add_argument('--mysql-dsn', default=os.getenv('MYSQL_DSN', ''))
    args = parser.parse_args()
    task = create_task('analyze_local_video', entity_type='video', entity_id=args.video_id or args.video, input_json=vars(args))
    update_task(task['task_id'], status='running', current_stage='analyze_local_video')
    script = ROOT / 'scripts' / 'analyze_local_video.py'
    cmd = [sys.executable, str(script), args.video, '--creator-slug', args.creator_slug]
    if args.video_id:
        cmd += ['--video-id', args.video_id]
    if args.desc:
        cmd += ['--desc', args.desc]
    if args.stats_json:
        cmd += ['--stats-json', args.stats_json]
    env = os.environ.copy()
    if args.mysql_dsn:
        env['MYSQL_DSN'] = args.mysql_dsn
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    append_step(task['task_id'], 'analyze_local_video', 'success' if proc.returncode == 0 else 'failed', input_ref={'video': args.video}, output_ref={'stdout': proc.stdout[-4000:]}, error_message=proc.stderr[-4000:])
    if proc.returncode != 0:
        update_task(task['task_id'], status='failed', error_message=proc.stderr[-2000:])
        sys.stderr.write(proc.stderr)
        return proc.returncode
    update_task(task['task_id'], status='success', current_stage='done')
    sys.stdout.write(proc.stdout)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
