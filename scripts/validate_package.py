from __future__ import annotations
import ast, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ROOT = ['SKILL.md','README.md','how_to_use.md','Project.md','.env.example','skills','tools','common','db','references','scripts']
MYSQL57_DENY_PATTERNS = ['JSON_TABLE','ROW_NUMBER','WITH RECURSIVE','GENERATED ALWAYS','utf8mb4_0900']
FORBIDDEN_PATH_MARKERS = ['legacy_runtime','original_pack']

def check_root_layout() -> list[str]:
    errors=[]
    for name in REQUIRED_ROOT:
        if not (ROOT/name).exists(): errors.append(f'缺少根目录必需项: {name}')
    if (ROOT/'legacy_runtime').exists(): errors.append('不应再包含 legacy_runtime 目录')
    return errors

def check_skill_files() -> list[str]:
    errors=[]
    for child in sorted((ROOT/'skills').iterdir()):
        if child.is_dir() and child.name!='__pycache__' and not (child/'SKILL.md').exists():
            errors.append(f'技能目录缺少 SKILL.md: {child.relative_to(ROOT)}')
    for child in sorted((ROOT/'tools').iterdir()):
        if not child.is_dir() or child.name=='__pycache__': continue
        if not ((child/'TOOL.md').exists() or (child/'SKILL.md').exists()):
            errors.append(f'工具目录缺少 TOOL.md 或 SKILL.md: {child.relative_to(ROOT)}')
        if not (child/'scripts'/'run.py').exists():
            errors.append(f'工具目录缺少 scripts/run.py: {child.relative_to(ROOT)}')
    return errors

def check_python39_parse() -> list[str]:
    errors=[]
    for path in ROOT.rglob('*.py'):
        if '__pycache__' in path.parts: continue
        try:
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path), feature_version=(3,9))
        except SyntaxError as exc:
            errors.append(f'Python 3.9 语法不兼容: {path.relative_to(ROOT)}: {exc.msg} @ {exc.lineno}:{exc.offset}')
    return errors

def check_mysql57_sql() -> list[str]:
    errors=[]
    for path in (ROOT/'db').glob('*.sql'):
        text=path.read_text(encoding='utf-8').upper()
        for marker in MYSQL57_DENY_PATTERNS:
            if marker in text: errors.append(f'MySQL 5.7 可疑语法: {path.relative_to(ROOT)} 包含 {marker}')
    return errors

def check_forbidden_legacy_refs() -> list[str]:
    errors=[]
    files=[]
    for target in [ROOT/'tools', ROOT/'common', ROOT/'skills', ROOT/'install.sh', ROOT/'requirements.txt']:
        if target.is_dir(): files.extend([p for p in target.rglob('*') if p.is_file()])
        elif target.exists(): files.append(target)
    for path in files:
        if '__pycache__' in path.parts: continue
        if path.suffix.lower() not in {'.py','.md','.sh','.txt','.json','.example','.sql'} and path.name not in {'SKILL.md','TOOL.md','.env.example'}: continue
        text=path.read_text(encoding='utf-8', errors='ignore')
        for marker in FORBIDDEN_PATH_MARKERS:
            if marker in text:
                errors.append(f'发现残留旧路径引用: {path.relative_to(ROOT)} 包含 {marker}')
                break
    return errors



def check_shell_scripts() -> list[str]:
    errors=[]
    for path in [ROOT/'install.sh']:
        proc=subprocess.run(['bash','-n', str(path)], capture_output=True, text=True)
        if proc.returncode != 0:
            errors.append(f"Shell 语法检查失败: {path.relative_to(ROOT)}: {proc.stderr.strip()}")
    return errors

def check_local_rag_config() -> list[str]:
    errors=[]
    if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
    try:
        from common.haystack_rag import RagConfig
    except Exception as exc:
        return [f'无法导入 common.haystack_rag: {exc}']
    old=dict(os.environ)
    try:
        os.environ.pop('HAYSTACK_QDRANT_MODE', None)
        os.environ['HAYSTACK_QDRANT_PATH']='/tmp/douyin-qdrant-local'
        cfg=RagConfig()
        if cfg.resolved_qdrant_mode()!='local': errors.append('本地 Qdrant 自动模式解析失败')
        os.environ['HAYSTACK_QDRANT_MODE']='memory'; os.environ.pop('HAYSTACK_QDRANT_PATH', None)
        cfg=RagConfig()
        if cfg.resolved_qdrant_mode()!='memory' or cfg.resolved_qdrant_location()!=':memory:': errors.append('Qdrant memory 模式解析失败')
        os.environ['HAYSTACK_QDRANT_MODE']='server'; os.environ['QDRANT_URL']='http://127.0.0.1:6333'
        cfg=RagConfig()
        if cfg.resolved_qdrant_mode()!='server' or cfg.resolved_qdrant_location()!='http://127.0.0.1:6333': errors.append('Qdrant server 模式解析失败')
    finally:
        os.environ.clear(); os.environ.update(old)
    return errors

def run_cmd(cmd:list[str], env:dict[str,str]):
    proc=subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr

def smoke_test() -> list[str]:
    errors=[]
    with tempfile.TemporaryDirectory(prefix='douyin_skills_v3_') as td:
        tmp=Path(td); workspace_root=tmp/'workspace_data'
        env=os.environ.copy()
        env['OPENCLAW_WORKSPACE_DATA_ROOT']=str(workspace_root)
        env['PYTHONPATH']=str(ROOT)+(os.pathsep+env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
        env['HAYSTACK_QDRANT_MODE']='local'
        env['HAYSTACK_QDRANT_PATH']=str(workspace_root/'qdrant_local')
        env['OPENCLAW_API_BASE']='http://127.0.0.1:11434/v1'; env['OPENCLAW_MODEL']='local-test-model'; env['OPENCLAW_EMBEDDING_MODEL']='local-test-embedding-model'
        video_src=tmp/'source.mp4'; audio_src=tmp/'source.mp3'; video_src.write_bytes(b'fake video bytes'); audio_src.write_bytes(b'fake audio bytes')
        payload={'aweme_detail': {'aweme_id':'1234567890','desc':'测试视频','author':{'uid':'uid_001','nickname':'测试作者','unique_id':'test_creator'},'video':{'duration':12000,'cover':{'url_list':[video_src.as_uri()]},'play_addr':{'url_list':[video_src.as_uri()]}},'music':{'id':'music_001','title':'测试音乐','author':'测试作者','play_url':{'url_list':[audio_src.as_uri()]}}}}
        payload_path=tmp/'payload.json'; payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        code,_,err=run_cmd([sys.executable, str(ROOT/'tools'/'resolve-video-source'/'scripts'/'run.py'), '--source','1234567890'], env)
        if code!=0: errors.append(f'resolve-video-source 失败: {err}')
        fetched=tmp/'fetched.json'
        code,_,err=run_cmd([sys.executable, str(ROOT/'tools'/'fetch-single-video-payload'/'scripts'/'run.py'), '--input-json', str(payload_path), '--output', str(fetched)], env)
        if code!=0 or not fetched.exists(): errors.append(f'fetch-single-video-payload 失败: {err}')
        code,out,err=run_cmd([sys.executable, str(ROOT/'tools'/'ingest-video-payload'/'scripts'/'run.py'), '--input-json', str(fetched), '--source-input','smoke-test'], env)
        if code!=0: errors.append(f'ingest-video-payload 失败: {err or out}')
        code,_,err=run_cmd([sys.executable, str(ROOT/'tools'/'update-task-state'/'scripts'/'run.py'), '--task-type','smoke','--status','success','--current-stage','done','--step-name','smoke_step'], env)
        if code!=0: errors.append(f'update-task-state 失败: {err}')
        script_json=tmp/'script.json'; script_json.write_text(json.dumps({'title':'测试脚本'}, ensure_ascii=False), encoding='utf-8')
        code,out,err=run_cmd([sys.executable, str(ROOT/'tools'/'save-script-version'/'scripts'/'run.py'), '--creator-slug','test_creator','--mode','create_from_topic','--topic','测试主题','--source-json', str(script_json)], env)
        if code!=0: errors.append(f'save-script-version 失败: {err or out}')
        kb_dir=workspace_root/'creators'/'test_creator'/'kb'; kb_dir.mkdir(parents=True, exist_ok=True)
        (kb_dir/'knowledge-base.json').write_text(json.dumps({'creator':{'creator_key':'test_creator','display_name':'测试作者'},'patterns':[{'pattern_id':'p1','category':'hook_type','summary':'开头先抛矛盾','evidence_count':1,'evidence_video_ids':['1234567890']}]}, ensure_ascii=False, indent=2), encoding='utf-8')
        news_req=tmp/'news_request.json'; news_req.write_text(json.dumps({'news_title':'测试新闻','news_summary':'这是一条测试新闻摘要','audience':'测试观众'}, ensure_ascii=False, indent=2), encoding='utf-8')
        code,out,err=run_cmd([sys.executable, str(ROOT/'tools'/'generate-news-video-package'/'scripts'/'run.py'), '--request-json', str(news_req), '--no-submit'], env)
        if code!=0: errors.append(f'generate-news-video-package 失败: {err or out}')
        for entity in ['creators','tasks','artifacts','scripts']:
            code,out,err=run_cmd([sys.executable, str(ROOT/'tools'/'list-library-entities'/'scripts'/'run.py'), '--entity', entity], env)
            if code!=0: errors.append(f'list-library-entities({entity}) 失败: {err or out}')
    return errors

def main() -> int:
    errors=[]
    errors+=check_root_layout(); errors+=check_skill_files(); errors+=check_python39_parse(); errors+=check_mysql57_sql(); errors+=check_forbidden_legacy_refs(); errors+=check_shell_scripts(); errors+=check_local_rag_config(); errors+=smoke_test()
    if errors:
        print(json.dumps({'ok':False, 'errors': errors}, ensure_ascii=False, indent=2)); return 1
    print(json.dumps({'ok':True, 'checks':['root_layout','skill_files','python39_parse','mysql57_sql','forbidden_legacy_refs','shell_scripts','local_rag_config','smoke_test']}, ensure_ascii=False, indent=2)); return 0
if __name__ == '__main__':
    raise SystemExit(main())
