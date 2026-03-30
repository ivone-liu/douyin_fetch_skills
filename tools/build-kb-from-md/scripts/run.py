from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.tasks import create_task, update_task, append_step
from common.storage import creator_root
from common.haystack_rag import RagConfig, index_analysis_dir_to_qdrant

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--creator-slug', default='')
    parser.add_argument('--analysis-md-dir', default='')
    parser.add_argument('--kb-dir', default='')
    parser.add_argument('--append', action='store_true')
    args = parser.parse_args()
    analysis_md_dir = Path(args.analysis_md_dir) if args.analysis_md_dir else creator_root(args.creator_slug) / 'analysis_md'
    kb_dir = Path(args.kb_dir) if args.kb_dir else creator_root(args.creator_slug) / 'kb'
    task = create_task('build_kb_from_md', entity_type='creator', entity_id=args.creator_slug, input_json={'analysis_md_dir': str(analysis_md_dir), 'kb_dir': str(kb_dir), 'append': args.append})
    update_task(task['task_id'], status='running', current_stage='index_qdrant')
    try:
        manifest = index_analysis_dir_to_qdrant(analysis_md_dir, kb_dir, recreate=not args.append, config=RagConfig())
    except Exception as exc:
        append_step(task['task_id'], 'index_qdrant', 'failed', error_message=str(exc))
        update_task(task['task_id'], status='failed', error_message=str(exc))
        raise
    append_step(task['task_id'], 'index_qdrant', 'success', output_ref={'knowledge_base_json': str(kb_dir / 'knowledge-base.json')})
    update_task(task['task_id'], status='success', current_stage='done', output_json=manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
