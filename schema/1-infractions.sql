CREATE TYPE infraction AS ENUM ('note', 'warning', 'mute', 'unmute', 'kick', 'ban', 'softban', 'unban');

CREATE TABLE IF NOT EXISTS infractions (
  id BIGINT NOT NULL,
  guild_id BIGINT NOT NULL REFERENCES guilds (id) ON DELETE CASCADE,

  -- IDs are local to guilds
  PRIMARY KEY (id, guild_id),

  type infraction NOT NULL,

  user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  actor_id BIGINT REFERENCES users (id) ON DELETE SET NULL,  -- Note: Check for this in code!

  reason TEXT,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS infractions_guild_id_user_id_idx ON infractions (guild_id, user_id);
