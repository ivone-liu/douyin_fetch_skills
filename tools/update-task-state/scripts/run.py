from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.tasks import create_task, update_task, append_step

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-id', default='')
    parser.add_argument('--task-type', default='generic')
    parser.add_argument('--status', required=True)
    parser.add_argument('--current-stage', default='')
    parser.add_argument('--entity-type', default='')
    parser.add_argument('--entity-id', default='')
    parser.add_argument('--error-message', default='')
    parser.add_argument('--step-name', default='')
    parser.add_argument('--input-ref', default='')
    parser.add_argument('--output-ref', default='')
    args = parser.parse_args()
    if args.task_id:
        task = update_task(args.task_id, status=args.status, current_stage=args.current_stage, error_message=args.error_message)
    else:
        task = create_task(args.task_type, entity_type=args.entity_type, entity_id=args.entity_id)
        task = update_task(task['task_id'], status=args.status, current_stage=args.current_stage, error_message=args.error_message)
    if args.step_name:
        input_ref = json.loads(args.input_ref) if args.input_ref else None
        output_ref = json.loads(args.output_ref) if args.output_ref else None
        append_step(task['task_id'], args.step_name, args.status, input_ref=input_ref, output_ref=output_ref, error_message=args.error_message)
    print(json.dumps(task, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
