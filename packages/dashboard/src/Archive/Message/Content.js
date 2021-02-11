import React from "react";
import SimpleMarkdown from "simple-markdown";

import "./Content.css";

export default function Content({ data }) {
  const { content, deleted_at: deletedAt, edited_at: editedAt, mentions } = data;

  // TODO: Render markdown etc.
  const deleted = deletedAt ? " deleted" : "";
  return <div className={"content" + deleted}>{content}</div>;
}
