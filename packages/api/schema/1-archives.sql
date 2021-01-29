CREATE TABLE IF NOT EXISTS archives (
  id BIGINT PRIMARY KEY,
  guild_id BIGINT NOT NULL REFERENCES guilds (id) ON DELETE CASCADE,

  -- Encrypted archive content
  -- As we only access these by ID everything is encrypted
  messages BYTEA NOT NULL,

  -- Authors and mentioned users
  -- Used to repopulate archive on fetch
  -- Without searching complete contents
  user_ids BIGINT[] NOT NULL DEFAULT '{}'
);
