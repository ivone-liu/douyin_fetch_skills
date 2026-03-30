from __future__ import annotations
import argparse, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--kb-json', required=True)
    parser.add_argument('--request-json', required=True)
    parser.add_argument('--output', default='')
    parser.add_argument('--top-k', type=int, default=10)
    args = parser.parse_args()
    script = ROOT / 'scripts' / 'generate_script.py'
    cmd = [sys.executable, str(script), args.kb_json, args.request_json, '--top-k', str(args.top_k)]
    if args.output:
        cmd += ['--output', args.output]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    proc = subprocess.run(cmd, check=False)
    return proc.returncode

if __name__ == '__main__':
    raise SystemExit(main())
