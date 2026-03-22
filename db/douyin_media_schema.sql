CREATE DATABASE IF NOT EXISTS openclaw_douyin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE openclaw_douyin;

CREATE TABLE IF NOT EXISTS creators (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sec_user_id VARCHAR(128) NULL,
  unique_id VARCHAR(128) NULL,
  display_name VARCHAR(255) NULL,
  avatar_url TEXT NULL,
  signature TEXT NULL,
  source_platform VARCHAR(32) NOT NULL DEFAULT 'douyin',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_creators_sec_user_id (sec_user_id),
  KEY idx_creators_unique_id (unique_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS videos (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  aweme_id VARCHAR(64) NOT NULL,
  creator_id BIGINT UNSIGNED NULL,
  desc_text TEXT NULL,
  create_time DATETIME NULL,
  duration_ms INT NULL,
  digg_count BIGINT NULL,
  comment_count BIGINT NULL,
  collect_count BIGINT NULL,
  share_count BIGINT NULL,
  play_count BIGINT NULL,
  cover_url TEXT NULL,
  play_url TEXT NULL,
  source_input TEXT NULL,
  raw_json_path VARCHAR(1024) NULL,
  normalized_json_path VARCHAR(1024) NULL,
  local_video_path VARCHAR(1024) NULL,
  local_analysis_md_path VARCHAR(1024) NULL,
  download_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  analysis_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  downloaded_at DATETIME NULL,
  analyzed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_videos_aweme_id (aweme_id),
  KEY idx_videos_creator_id (creator_id),
  KEY idx_videos_download_status (download_status),
  KEY idx_videos_analysis_status (analysis_status),
  CONSTRAINT fk_videos_creator_id FOREIGN KEY (creator_id) REFERENCES creators(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS music_assets (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  music_id VARCHAR(128) NULL,
  title VARCHAR(255) NULL,
  author_name VARCHAR(255) NULL,
  play_url TEXT NULL,
  duration_ms INT NULL,
  local_music_path VARCHAR(1024) NULL,
  download_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  downloaded_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_music_assets_music_id (music_id),
  KEY idx_music_assets_download_status (download_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS video_music_map (
  video_id BIGINT UNSIGNED NOT NULL,
  music_id BIGINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (video_id, music_id),
  CONSTRAINT fk_video_music_map_video_id FOREIGN KEY (video_id) REFERENCES videos(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_video_music_map_music_id FOREIGN KEY (music_id) REFERENCES music_assets(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS api_fetch_logs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_type VARCHAR(64) NOT NULL,
  source_input TEXT NULL,
  endpoint_name VARCHAR(255) NULL,
  request_params_json JSON NULL,
  response_code INT NULL,
  raw_json_path VARCHAR(1024) NULL,
  aweme_id VARCHAR(64) NULL,
  fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_api_fetch_logs_source_type (source_type),
  KEY idx_api_fetch_logs_aweme_id (aweme_id),
  KEY idx_api_fetch_logs_fetched_at (fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
