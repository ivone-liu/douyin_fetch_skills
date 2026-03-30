from __future__ import annotations
import argparse, os, sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.tasks import create_task, update_task, append_step

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-json', required=True)
    parser.add_argument('--source-input', default='')
    parser.add_argument('--endpoint-name', default='hybrid_video_data')
    parser.add_argument('--run-analysis', action='store_true')
    parser.add_argument('--mysql-dsn', default=os.getenv('MYSQL_DSN', ''))
    args = parser.parse_args()
    task = create_task('ingest_video_payload', entity_type='video_payload', entity_id=args.input_json, input_json=vars(args))
    update_task(task['task_id'], status='running', current_stage='pipeline_ingest')
    script = ROOT / 'scripts' / 'pipeline_ingest_single_video.py'
    cmd = [sys.executable, str(script), args.input_json, '--source-input', args.source_input, '--endpoint-name', args.endpoint_name]
    if args.run_analysis:
        cmd.append('--run-analysis')
    env = os.environ.copy()
    if args.mysql_dsn:
        env['MYSQL_DSN'] = args.mysql_dsn
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    append_step(task['task_id'], 'pipeline_ingest', 'success' if proc.returncode == 0 else 'failed', input_ref={'input_json': args.input_json}, output_ref={'stdout': proc.stdout[-4000:]}, error_message=proc.stderr[-4000:])
    if proc.returncode != 0:
        update_task(task['task_id'], status='failed', error_message=proc.stderr[-2000:])
        sys.stderr.write(proc.stderr)
        return proc.returncode
    update_task(task['task_id'], status='success', current_stage='done')
    sys.stdout.write(proc.stdout)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
