from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.creator_registry import load_subscriptions
import subprocess

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile-url', default='')
    parser.add_argument('--creator-key', default='')
    parser.add_argument('--max-pages', type=int, default=1)
    args = parser.parse_args()
    subscriptions = load_subscriptions()
    target = None
    for row in subscriptions:
        if args.creator_key and row.get('creator_key') == args.creator_key:
            target = row
            break
        if args.profile_url and row.get('profile_url') == args.profile_url:
            target = row
            break
    if target is None:
        raise SystemExit('Subscription not found. Subscribe first or pass an explicit creator key.')
    cmd = [sys.executable, str(ROOT / 'tools' / 'fetch-creator-feed' / 'scripts' / 'run.py')]
    if target.get('profile_url'):
        cmd += ['--profile-url', str(target['profile_url'])]
    if target.get('sec_user_id'):
        cmd += ['--sec-user-id', str(target['sec_user_id'])]
    if target.get('unique_id'):
        cmd += ['--unique-id', str(target['unique_id'])]
    cmd += ['--max-pages', str(args.max_pages)]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode

if __name__ == '__main__':
    raise SystemExit(main())
