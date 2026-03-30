CREATE TABLE IF NOT EXISTS render_tasks (
  render_task_id VARCHAR(64) PRIMARY KEY,
  script_id VARCHAR(64) NULL,
  provider VARCHAR(64) NOT NULL,
  provider_task_id VARCHAR(255) NULL,
  mode VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  request_json JSON NULL,
  response_json JSON NULL,
  result_video_path TEXT NULL,
  created_at DATETIME NOT NULL,
  finished_at DATETIME NULL
);
