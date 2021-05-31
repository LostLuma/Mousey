import React from "react";

import "./Attachment.css";

export default function Attachment({ path }) {
  const url = `https://cdn.discordapp.com${path}`;
  const [, filename] = /^\/attachments(?:\/\d+){2}\/(.+)/u.exec(path);

  return (
    <div className="attachment">
      <a href={url} target="_blank" rel="noopener noreferrer">
        <img src={url} alt={filename} loading="lazy" />
      </a>
    </div>
  );
}
