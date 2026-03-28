This skill uses environment-driven Volcengine config because deployment setups vary.

Minimum required env:

```bash
VOLCENGINE_VIDEO_SUBMIT_URL=...
```

Common env:

```bash
VOLCENGINE_API_KEY=...
VOLCENGINE_VIDEO_AUTH_SCHEME=Bearer
VOLCENGINE_VIDEO_MODEL=...
VOLCENGINE_VIDEO_MODEL_VERSION=...
VOLCENGINE_VIDEO_MAX_DURATION_SECONDS=12
VOLCENGINE_VIDEO_REQUEST_TEMPLATE_JSON='{"model":"{{model}}","prompt":"{{prompt}}","negative_prompt":"{{negative_prompt}}","duration":"{{duration_seconds}}","ratio":"{{aspect_ratio}}"}'
VOLCENGINE_VIDEO_TASK_ID_PATHS='id,task_id,data.id,data.task_id'
VOLCENGINE_VIDEO_STATUS_URL_TEMPLATE='https://.../{task_id}'
VOLCENGINE_VIDEO_STATUS_PATHS='status,data.status'
VOLCENGINE_VIDEO_RESULT_URL_PATHS='video_url,data.video_url,output.video_url'
```

You can also override the workspace data root:

```bash
OPENCLAW_WORKSPACE_DATA_ROOT=~/.openclaw/workspace/data
```
