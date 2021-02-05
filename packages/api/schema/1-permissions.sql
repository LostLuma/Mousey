CREATE TABLE IF NOT EXISTS required_roles (
  guild_id BIGINT PRIMARY KEY REFERENCES guilds (id) ON DELETE CASCADE,
  required_roles BIGINT[] NOT NULL DEFAULT '{}'
);
