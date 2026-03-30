from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .json_utils import first_non_empty_path


def _env_int(*names: str, default: int) -> int:
    for name in names:
        raw = os.getenv(name)
        if raw is None or str(raw).strip() == '':
            continue
        try:
            return int(str(raw).strip())
        except ValueError:
            continue
    return default


DEFAULT_ARK_BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'
ARK_BASE_URL = (os.getenv('VOLCENGINE_ARK_BASE_URL') or os.getenv('ARK_BASE_URL') or DEFAULT_ARK_BASE_URL).rstrip('/')
ARK_SUBMIT_URL = f'{ARK_BASE_URL}/contents/generations/tasks'
ARK_STATUS_URL_TEMPLATE = f'{ARK_BASE_URL}/contents/generations/tasks/{{task_id}}'
ARK_MODEL = os.getenv('VOLCENGINE_VIDEO_MODEL') or os.getenv('ARK_MODEL') or 'doubao-seedance-1-5-pro-251215'
ARK_MAX_DURATION_SECONDS = _env_int('VOLCENGINE_VIDEO_DURATION_SECONDS', 'ARK_MAX_DURATION_SECONDS', default=5)
ARK_TASK_ID_PATHS = ['id', 'task_id', 'data.id', 'data.task_id']
ARK_STATUS_PATHS = ['status', 'data.status']
ARK_RESULT_URL_PATHS = [
    'content.video_url',
    'content.video_urls.0',
    'data.content.video_url',
    'data.content.video_urls.0',
    'video_url',
    'data.video_url',
]
ARK_SUCCESS_VALUES = {'succeeded', 'success', 'done', 'completed'}
ARK_FAILURE_VALUES = {'failed', 'error', 'cancelled'}
ARK_TIMEOUT_SECONDS = 60
ARK_POLL_INTERVAL_SECONDS = 8
ARK_MAX_POLL_ATTEMPTS = 45


@dataclass
class VolcengineVideoConfig:
    submit_url: str = ARK_SUBMIT_URL
    status_url_template: str = ARK_STATUS_URL_TEMPLATE
    method: str = 'POST'
    status_method: str = 'GET'
    model: str = ARK_MODEL
    max_duration_seconds: int = ARK_MAX_DURATION_SECONDS
    auth_header: str = 'Authorization'
    auth_value: str = ''
    timeout_seconds: int = ARK_TIMEOUT_SECONDS
    poll_interval_seconds: int = ARK_POLL_INTERVAL_SECONDS
    max_poll_attempts: int = ARK_MAX_POLL_ATTEMPTS


class VolcengineVideoError(RuntimeError):
    pass


def load_config_from_env() -> VolcengineVideoConfig:
    api_key = (os.getenv('ARK_API_KEY') or os.getenv('VOLCENGINE_ARK_API_KEY') or '').strip()
    if not api_key:
        raise VolcengineVideoError('Missing ARK_API_KEY or VOLCENGINE_ARK_API_KEY in environment.')
    return VolcengineVideoConfig(auth_value=f'Bearer {api_key}')


class VolcengineVideoClient:
    def __init__(self, config: Optional[VolcengineVideoConfig] = None):
        self.config = config or load_config_from_env()
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            self.config.auth_header: self.config.auth_value,
        })

    @staticmethod
    def _as_bool_string(value: Any, default: bool) -> str:
        if value is None:
            return 'true' if default else 'false'
        if isinstance(value, bool):
            return 'true' if value else 'false'
        raw = str(value).strip().lower()
        return 'true' if raw in {'1', 'true', 'yes', 'y', 'on'} else 'false'

    def _append_seedance_flags(self, prompt: str, context: Dict[str, Any]) -> str:
        duration = int(context.get('duration_seconds') or self.config.max_duration_seconds)
        watermark = self._as_bool_string(context.get('watermark'), True)
        camera_fixed = self._as_bool_string(context.get('camera_fixed'), False)
        prompt = (prompt or '').strip()
        if '--duration' in prompt:
            return prompt
        return f"{prompt} --duration {duration} --camerafixed {camera_fixed} --watermark {watermark}".strip()

    def _build_payload(self, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._append_seedance_flags(str(context.get('prompt') or ''), context)
        image_url = context.get('reference_image_url') or context.get('image_url')
        if not image_url:
            raise VolcengineVideoError('Missing reference_image_url. Ark 图生视频 submission requires a reachable image URL.')
        return {
            'model': self.config.model,
            'content': [
                {
                    'type': 'text',
                    'text': prompt,
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': str(image_url),
                    },
                },
            ],
        }

    def _request(self, method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {'timeout': self.config.timeout_seconds}
        if method.upper() != 'GET':
            kwargs['json'] = payload
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception as exc:
            raise VolcengineVideoError(f'Expected JSON response from {url}, got non-JSON body.') from exc

    def submit(self, context: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._build_payload(context)
        response = self._request(self.config.method, self.config.submit_url, payload)
        return {'request_payload': payload, 'response_payload': response}

    def extract_task_id(self, payload: Dict[str, Any]) -> Optional[str]:
        value = first_non_empty_path(payload, ARK_TASK_ID_PATHS)
        return None if value in (None, '') else str(value)

    def extract_status(self, payload: Dict[str, Any]) -> Optional[str]:
        value = first_non_empty_path(payload, ARK_STATUS_PATHS)
        return None if value in (None, '') else str(value).strip().lower()

    def extract_result_urls(self, payload: Dict[str, Any]) -> List[str]:
        value = first_non_empty_path(payload, ARK_RESULT_URL_PATHS)
        if value in (None, ''):
            return []
        if isinstance(value, list):
            return [str(x) for x in value if x]
        return [str(value)]

    def poll(self, task_id: str) -> Dict[str, Any]:
        status_url = self.config.status_url_template.format(task_id=task_id, id=task_id)
        for attempt in range(1, self.config.max_poll_attempts + 1):
            response = self._request(self.config.status_method, status_url)
            status = self.extract_status(response)
            urls = self.extract_result_urls(response)
            if urls and (status is None or status in ARK_SUCCESS_VALUES):
                return {
                    'task_id': task_id,
                    'status': status or 'completed',
                    'response_payload': response,
                    'result_urls': urls,
                    'attempt': attempt,
                }
            if status in ARK_FAILURE_VALUES:
                raise VolcengineVideoError(f'Generation task failed with status={status}: {response}')
            time.sleep(self.config.poll_interval_seconds)
        raise VolcengineVideoError(f'Generation task timed out after {self.config.max_poll_attempts} polling attempts.')

    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        submit_result = self.submit(context)
        task_id = self.extract_task_id(submit_result['response_payload'])
        if not task_id:
            raise VolcengineVideoError(f'Unable to extract task id from response: {submit_result["response_payload"]}')
        poll_result = self.poll(task_id)
        return {
            'task_id': task_id,
            'submit': submit_result,
            'poll': poll_result,
            'result_urls': poll_result.get('result_urls') or [],
        }

    def download_results(self, urls: List[str], output_dir: Path) -> List[str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        saved: List[str] = []
        for idx, url in enumerate(urls, start=1):
            resp = self.session.get(url, timeout=self.config.timeout_seconds, stream=True)
            resp.raise_for_status()
            suffix = Path(url.split('?')[0]).suffix or '.mp4'
            target = output_dir / f'ark_video_{idx}{suffix}'
            with open(target, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            saved.append(str(target))
        return saved
