CREATE TABLE IF NOT EXISTS reminders (
  idx BIGSERIAL PRIMARY KEY,

  user_id BIGINT REFERENCES users (id) ON DELETE CASCADE,
  guild_id BIGINT REFERENCES guilds (id) ON DELETE CASCADE,

  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,

  expires_at TIMESTAMP NOT NULL,
  message TEXT NOT NULL DEFAULT 'something'
);

CREATE INDEX IF NOT EXISTS reminders_guild_id_expires_at_idx ON reminders (guild_id, expires_at);
