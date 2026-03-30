CREATE TABLE IF NOT EXISTS task_runs (
  task_id VARCHAR(64) PRIMARY KEY,
  task_type VARCHAR(64) NOT NULL,
  entity_type VARCHAR(64) NULL,
  entity_id VARCHAR(255) NULL,
  parent_task_id VARCHAR(64) NULL,
  status VARCHAR(32) NOT NULL,
  current_stage VARCHAR(64) NULL,
  input_json JSON NULL,
  output_json JSON NULL,
  created_at DATETIME NOT NULL,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  error_message TEXT NULL
);

CREATE TABLE IF NOT EXISTS task_steps (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  task_id VARCHAR(64) NOT NULL,
  step_name VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL,
  input_ref JSON NULL,
  output_ref JSON NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL,
  INDEX idx_task_steps_task_id (task_id)
);
