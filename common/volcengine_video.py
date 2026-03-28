from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .json_utils import first_non_empty_path, render_template_obj


@dataclass
class VolcengineVideoConfig:
    submit_url: str
    status_url_template: Optional[str]
    method: str
    status_method: str
    model: Optional[str]
    model_version: Optional[str]
    max_duration_seconds: int
    auth_header: str
    auth_value: str
    extra_headers: Dict[str, str]
    request_template: Dict[str, Any]
    status_request_template: Optional[Dict[str, Any]]
    task_id_paths: List[str]
    status_paths: List[str]
    success_values: List[str]
    failure_values: List[str]
    result_url_paths: List[str]
    timeout_seconds: int
    poll_interval_seconds: int
    max_poll_attempts: int


class VolcengineVideoError(RuntimeError):
    pass


def _json_env(name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    raw = os.getenv(name)
    if not raw:
        return default or {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VolcengineVideoError(f'Environment variable {name} is not valid JSON: {exc}') from exc
    if not isinstance(value, dict):
        raise VolcengineVideoError(f'Environment variable {name} must be a JSON object.')
    return value


def load_config_from_env() -> VolcengineVideoConfig:
    submit_url = os.getenv('VOLCENGINE_VIDEO_SUBMIT_URL', '').strip()
    if not submit_url:
        raise VolcengineVideoError('Missing VOLCENGINE_VIDEO_SUBMIT_URL in environment.')
    auth_header = os.getenv('VOLCENGINE_VIDEO_AUTH_HEADER', 'Authorization').strip()
    auth_value = os.getenv('VOLCENGINE_VIDEO_AUTH_VALUE', '').strip()
    if not auth_value:
        api_key = os.getenv('VOLCENGINE_API_KEY', '').strip()
        if api_key:
            scheme = os.getenv('VOLCENGINE_VIDEO_AUTH_SCHEME', 'Bearer').strip()
            auth_value = f'{scheme} {api_key}'.strip()
    request_template = _json_env('VOLCENGINE_VIDEO_REQUEST_TEMPLATE_JSON', default={})
    status_request_template = _json_env('VOLCENGINE_VIDEO_STATUS_REQUEST_TEMPLATE_JSON', default={}) or None
    success_values = [x.strip().lower() for x in os.getenv('VOLCENGINE_VIDEO_SUCCESS_VALUES', 'succeeded,success,done,completed').split(',') if x.strip()]
    failure_values = [x.strip().lower() for x in os.getenv('VOLCENGINE_VIDEO_FAILURE_VALUES', 'failed,error,cancelled').split(',') if x.strip()]
    task_id_paths = [x.strip() for x in os.getenv('VOLCENGINE_VIDEO_TASK_ID_PATHS', 'id,task_id,data.id,data.task_id,output.id').split(',') if x.strip()]
    status_paths = [x.strip() for x in os.getenv('VOLCENGINE_VIDEO_STATUS_PATHS', 'status,data.status,task.status,output.status').split(',') if x.strip()]
    result_url_paths = [x.strip() for x in os.getenv('VOLCENGINE_VIDEO_RESULT_URL_PATHS', 'video_url,data.video_url,output.video_url,result.video_url,data.output.video_url,data.video_urls.0,output.video_urls.0,result.video_urls.0').split(',') if x.strip()]
    return VolcengineVideoConfig(
        submit_url=submit_url,
        status_url_template=os.getenv('VOLCENGINE_VIDEO_STATUS_URL_TEMPLATE', '').strip() or None,
        method=os.getenv('VOLCENGINE_VIDEO_SUBMIT_METHOD', 'POST').upper(),
        status_method=os.getenv('VOLCENGINE_VIDEO_STATUS_METHOD', 'GET').upper(),
        model=os.getenv('VOLCENGINE_VIDEO_MODEL', '').strip() or None,
        model_version=os.getenv('VOLCENGINE_VIDEO_MODEL_VERSION', '').strip() or None,
        max_duration_seconds=int(os.getenv('VOLCENGINE_VIDEO_MAX_DURATION_SECONDS', '12')),
        auth_header=auth_header,
        auth_value=auth_value,
        extra_headers={k: str(v) for k, v in _json_env('VOLCENGINE_VIDEO_EXTRA_HEADERS_JSON', default={}).items()},
        request_template=request_template,
        status_request_template=status_request_template,
        task_id_paths=task_id_paths,
        status_paths=status_paths,
        success_values=success_values,
        failure_values=failure_values,
        result_url_paths=result_url_paths,
        timeout_seconds=int(os.getenv('VOLCENGINE_VIDEO_TIMEOUT_SECONDS', '60')),
        poll_interval_seconds=int(os.getenv('VOLCENGINE_VIDEO_POLL_INTERVAL_SECONDS', '8')),
        max_poll_attempts=int(os.getenv('VOLCENGINE_VIDEO_MAX_POLL_ATTEMPTS', '45')),
    )


class VolcengineVideoClient:
    def __init__(self, config: Optional[VolcengineVideoConfig] = None):
        self.config = config or load_config_from_env()
        self.session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        if self.config.auth_value:
            headers[self.config.auth_header] = self.config.auth_value
        headers.update(self.config.extra_headers)
        self.session.headers.update(headers)

    def _build_payload(self, template: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        payload = render_template_obj(template, context)
        if not payload:
            payload = {
                'model': context.get('model'),
                'model_version': context.get('model_version'),
                'prompt': context.get('prompt'),
                'negative_prompt': context.get('negative_prompt'),
                'duration': context.get('duration_seconds'),
                'duration_seconds': context.get('duration_seconds'),
                'aspect_ratio': context.get('aspect_ratio'),
            }
        return {k: v for k, v in payload.items() if v not in (None, '', [], {})}

    def _request(self, method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = self.session.request(method, url, json=payload, timeout=self.config.timeout_seconds)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception as exc:
            raise VolcengineVideoError(f'Expected JSON response from {url}, got non-JSON body.') from exc

    def submit(self, context: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._build_payload(self.config.request_template, context)
        response = self._request(self.config.method, self.config.submit_url, payload)
        return {'request_payload': payload, 'response_payload': response}

    def extract_task_id(self, payload: Dict[str, Any]) -> Optional[str]:
        value = first_non_empty_path(payload, self.config.task_id_paths)
        return None if value in (None, '') else str(value)

    def extract_status(self, payload: Dict[str, Any]) -> Optional[str]:
        value = first_non_empty_path(payload, self.config.status_paths)
        return None if value in (None, '') else str(value).strip().lower()

    def extract_result_urls(self, payload: Dict[str, Any]) -> List[str]:
        value = first_non_empty_path(payload, self.config.result_url_paths)
        if value in (None, ''):
            return []
        if isinstance(value, list):
            return [str(x) for x in value if x]
        return [str(value)]

    def poll(self, task_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.config.status_url_template:
            raise VolcengineVideoError('Missing VOLCENGINE_VIDEO_STATUS_URL_TEMPLATE for polling.')
        status_url = self.config.status_url_template.format(task_id=task_id)
        for attempt in range(1, self.config.max_poll_attempts + 1):
            payload = None
            if self.config.status_method != 'GET':
                payload = self._build_payload(self.config.status_request_template or {}, {**context, 'task_id': task_id})
            response = self._request(self.config.status_method, status_url, payload)
            status = self.extract_status(response)
            urls = self.extract_result_urls(response)
            if urls and (status is None or status in self.config.success_values):
                return {'status': status or 'completed', 'response_payload': response, 'result_urls': urls, 'attempts': attempt}
            if status in self.config.success_values:
                return {'status': status, 'response_payload': response, 'result_urls': urls, 'attempts': attempt}
            if status in self.config.failure_values:
                raise VolcengineVideoError(f'Volcengine task {task_id} failed with status={status}.')
            time.sleep(self.config.poll_interval_seconds)
        raise VolcengineVideoError(f'Polling exceeded {self.config.max_poll_attempts} attempts for task {task_id}.')

    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        submit_result = self.submit(context)
        submit_payload = submit_result['response_payload']
        direct_urls = self.extract_result_urls(submit_payload)
        if direct_urls:
            return {
                'mode': 'sync',
                'request_payload': submit_result['request_payload'],
                'submit_response': submit_payload,
                'result_urls': direct_urls,
                'task_id': self.extract_task_id(submit_payload),
                'status': self.extract_status(submit_payload) or 'completed',
            }
        task_id = self.extract_task_id(submit_payload)
        if not task_id:
            raise VolcengineVideoError('Submit response did not include a task id or direct video url.')
        poll_result = self.poll(task_id, context)
        return {
            'mode': 'async',
            'request_payload': submit_result['request_payload'],
            'submit_response': submit_payload,
            'poll_response': poll_result['response_payload'],
            'result_urls': poll_result.get('result_urls', []),
            'task_id': task_id,
            'status': poll_result.get('status'),
            'poll_attempts': poll_result.get('attempts'),
        }

    def download_results(self, result_urls: List[str], output_dir: Path) -> List[str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for idx, url in enumerate(result_urls, start=1):
            resp = self.session.get(url, timeout=self.config.timeout_seconds, stream=True)
            resp.raise_for_status()
            suffix = '.mp4'
            content_type = resp.headers.get('Content-Type', '')
            if 'quicktime' in content_type:
                suffix = '.mov'
            path = output_dir / f'generated_{idx}{suffix}'
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
            saved.append(str(path))
        return saved
