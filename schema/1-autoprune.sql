CREATE TYPE activity_type AS ENUM('joined', 'seen', 'status');

CREATE TABLE IF NOT EXISTS autoprune (
  guild_id BIGINT PRIMARY KEY REFERENCES guilds (id) ON DELETE CASCADE,

  -- Includes users with these roles
  -- When empty users without roles are purged
  role_ids BIGINT[],

  activity_type activity_type,

  -- How long until users are purged
  inactive_timeout INTERVAL NOT NULL,

  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
