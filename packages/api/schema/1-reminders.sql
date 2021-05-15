CREATE TABLE IF NOT EXISTS reminders (
  id BIGSERIAL PRIMARY KEY,

  user_id BIGINT REFERENCES users (id) ON DELETE CASCADE,
  guild_id BIGINT REFERENCES guilds (id) ON DELETE CASCADE,

  channel_id BIGINT NOT NULL REFERENCES channels (id) ON DELETE CASCADE,

  message_id BIGINT NOT NULL,
  referenced_message_id BIGINT,  -- Users can reply to messages to remind about them instead

  expires_at TIMESTAMP NOT NULL,
  message TEXT NOT NULL DEFAULT 'something'
);

CREATE INDEX IF NOT EXISTS reminders_guild_id_expires_at_idx ON reminders (guild_id, expires_at);
