CREATE TABLE IF NOT EXISTS script_versions (
  script_id VARCHAR(64) PRIMARY KEY,
  parent_script_id VARCHAR(64) NULL,
  creator_key VARCHAR(255) NULL,
  topic VARCHAR(512) NULL,
  mode VARCHAR(64) NOT NULL,
  content_json JSON NULL,
  content_md_path TEXT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
