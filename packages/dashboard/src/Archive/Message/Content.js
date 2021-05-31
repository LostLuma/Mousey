import React from "react";
// import SimpleMarkdown from "simple-markdown";

import "./Content.css";

export default function Content({ data }) {
  // const { content, edited_at: editedAt, mentions } = data;
  return <div className="content">{data.content}</div>;
}
