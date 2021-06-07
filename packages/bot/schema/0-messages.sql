CREATE TABLE IF NOT EXISTS messages (
  id BIGINT PRIMARY KEY,

  author_id BIGINT,  -- NULL to distinguish webhook messages
  channel_id BIGINT NOT NULL,

  content BYTEA NOT NULL,

  embeds BYTEA[] NOT NULL DEFAULT '{}',
  attachments BYTEA[] NOT NULL DEFAULT '{}',

  edited_at TIMESTAMP WITH TIME ZONE,
  deleted_at TIMESTAMP WITH TIME ZONE
);
