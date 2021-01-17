CREATE TABLE IF NOT EXISTS status_updates (
  user_id BIGINT PRIMARY KEY,
  updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS seen_updates (
  guild_id BIGINT NOT NULL REFERENCES guilds (id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL,

  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS spoke_updates (
  guild_id BIGINT NOT NULL REFERENCES guilds (id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL,

  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (guild_id, user_id)
);
