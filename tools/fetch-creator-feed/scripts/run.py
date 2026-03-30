from __future__ import annotations
import argparse, json, os, sys, subprocess, shutil, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import datetime
from common.tikhub import TikHubClient
from common.storage import creator_root, slugify
from common.creator_registry import upsert_subscription
from common.tasks import create_task, update_task, append_step
from tools.fetch_creator_feed_normalize_stub import normalize_items

def _extract_sec_user_id(response: dict) -> str:
    data = response.get('data') or response
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            for key in ('sec_user_id', 'sec_uid', 'value'):
                if first.get(key):
                    return str(first[key])
    if isinstance(data, dict):
        for key in ('sec_user_id', 'sec_uid', 'value'):
            if data.get(key):
                return str(data[key])
    return ''

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile-url', default='')
    parser.add_argument('--sec-user-id', default='')
    parser.add_argument('--unique-id', default='')
    parser.add_argument('--max-pages', type=int, default=1)
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--sort-type', type=int, default=0)
    args = parser.parse_args()

    task = create_task('fetch_creator_feed', entity_type='creator', entity_id=args.sec_user_id or args.unique_id or args.profile_url, input_json=vars(args))
    update_task(task['task_id'], status='running', current_stage='resolve_creator')
    client = TikHubClient()
    sec_user_id = args.sec_user_id.strip()
    if not sec_user_id and args.profile_url.strip():
        resp = client.extract_sec_user_id(args.profile_url.strip())
        sec_user_id = _extract_sec_user_id(resp)
        append_step(task['task_id'], 'extract_sec_user_id', 'success', input_ref={'profile_url': args.profile_url}, output_ref={'sec_user_id': sec_user_id})
    if not sec_user_id and not args.unique_id.strip():
        update_task(task['task_id'], status='failed', error_message='Could not resolve sec_user_id or unique_id')
        raise SystemExit('Could not resolve sec_user_id or unique_id')

    creator_key = sec_user_id or args.unique_id.strip() or slugify(args.profile_url)
    croot = creator_root(creator_key)
    raw_dir = croot / 'raw_api' / 'douyin_user_feed' / datetime.now().strftime('%Y-%m-%d')
    raw_dir.mkdir(parents=True, exist_ok=True)
    all_items = []
    max_cursor = 0
    for page in range(1, args.max_pages + 1):
        payload = client.fetch_user_posts(sec_user_id=sec_user_id, unique_id=args.unique_id.strip(), max_cursor=max_cursor, count=args.count, sort_type=args.sort_type)
        (raw_dir / f'page_{page:03d}.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        data = payload.get('data') or {}
        items = data.get('aweme_list') or data.get('items') or []
        all_items.extend(items)
        append_step(task['task_id'], 'fetch_page', 'success', input_ref={'page': page, 'max_cursor': max_cursor}, output_ref={'count': len(items)})
        max_cursor = int(data.get('max_cursor') or data.get('cursor') or 0)
        has_more = bool(data.get('has_more'))
        if not has_more:
            break
    normalized = normalize_items(all_items)
    norm_dir = croot / 'normalized' / 'douyin_user_feed'
    norm_dir.mkdir(parents=True, exist_ok=True)
    norm_path = norm_dir / 'latest.json'
    norm_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding='utf-8')
    upsert_subscription({
        'creator_key': creator_key,
        'sec_user_id': sec_user_id,
        'unique_id': args.unique_id.strip(),
        'profile_url': args.profile_url.strip(),
        'status': 'active',
        'sync_mode': 'manual',
        'last_synced_at': datetime.utcnow().isoformat() + 'Z',
    })
    update_task(task['task_id'], status='success', current_stage='done', output_json={'creator_key': creator_key, 'normalized_path': str(norm_path), 'item_count': len(normalized)})
    print(json.dumps({'task_id': task['task_id'], 'creator_key': creator_key, 'normalized_path': str(norm_path), 'item_count': len(normalized)}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
