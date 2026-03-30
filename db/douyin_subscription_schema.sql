CREATE TABLE IF NOT EXISTS creator_subscriptions (
  subscription_id VARCHAR(64) PRIMARY KEY,
  creator_id BIGINT NULL,
  creator_key VARCHAR(255) NOT NULL,
  sec_user_id VARCHAR(255) NULL,
  unique_id VARCHAR(255) NULL,
  profile_url TEXT NULL,
  status VARCHAR(32) NOT NULL,
  sync_mode VARCHAR(32) NOT NULL,
  latest_seen_video_time DATETIME NULL,
  last_synced_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_creator_key (creator_key)
);
