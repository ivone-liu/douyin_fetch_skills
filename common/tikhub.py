from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = 'https://api.tikhub.io'
HYBRID_VIDEO_ENDPOINT = '/api/v1/hybrid/video_data'
FETCH_ONE_VIDEO_ENDPOINT = '/api/v1/douyin/web/fetch_one_video'
EXTRACT_SEC_USER_ID_ENDPOINT = '/api/v1/douyin/web/get_all_sec_user_id'
FETCH_USER_POST_VIDEOS_V2_ENDPOINT = '/api/v1/douyin/app/v3/fetch_user_post_videos_v2'
FETCH_USER_POST_VIDEOS_V1_ENDPOINT = '/api/v1/douyin/app/v3/fetch_user_post_videos'


class TikHubError(RuntimeError):
    pass


class TikHubClient:
    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv('TIKHUB_BASE_URL') or DEFAULT_BASE_URL).rstrip('/')
        self.token = (token or os.getenv('TIKHUB_API_TOKEN') or '').strip()
        if not self.token:
            raise TikHubError('Missing TIKHUB_API_TOKEN')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
            'User-Agent': 'douyin-skills-v2/1.0',
        })

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.get(f'{self.base_url}{endpoint}', params=params, timeout=120)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception as exc:
            raise TikHubError(f'Expected JSON from TikHub endpoint {endpoint}') from exc

    def _post(self, endpoint: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(f'{self.base_url}{endpoint}', json=json_body, timeout=120)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception as exc:
            raise TikHubError(f'Expected JSON from TikHub endpoint {endpoint}') from exc

    def fetch_video_by_url(self, url: str) -> Dict[str, Any]:
        return self._get(HYBRID_VIDEO_ENDPOINT, {'url': url})

    def fetch_video_by_aweme_id(self, aweme_id: str, need_anchor_info: bool = False) -> Dict[str, Any]:
        return self._get(FETCH_ONE_VIDEO_ENDPOINT, {'aweme_id': aweme_id, 'need_anchor_info': str(bool(need_anchor_info)).lower()})

    def extract_sec_user_id(self, profile_url: str) -> Dict[str, Any]:
        return self._post(EXTRACT_SEC_USER_ID_ENDPOINT, {'url': [profile_url]})

    def fetch_user_posts(self, sec_user_id: str = '', unique_id: str = '', max_cursor: int = 0, count: int = 20, sort_type: int = 0) -> Dict[str, Any]:
        params: Dict[str, Any] = {'max_cursor': max_cursor, 'count': count, 'sort_type': sort_type}
        if sec_user_id:
            params['sec_user_id'] = sec_user_id
        if unique_id:
            params['unique_id'] = unique_id
        try:
            return self._get(FETCH_USER_POST_VIDEOS_V2_ENDPOINT, params)
        except Exception:
            return self._get(FETCH_USER_POST_VIDEOS_V1_ENDPOINT, params)
