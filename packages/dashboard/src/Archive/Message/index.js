import React from "react";

import { snowflakeTime } from "../utils";
import Attachment from "./Attachment";
import Author from "./Author";
import Avatar from "./Avatar";
import Content from "./Content";
import Timestamp from "./Timestamp";

import "./index.css";

export default function Message({ data }) {
  const { attachments, author, channel, deleted_at: deletedAt, embeds, id } = data;

  const className = "message" + (deletedAt ? " deleted" : "");

  return (
    <div className={className}>
      <Avatar user={author} />
      <Author user={author} />
      <Timestamp date={snowflakeTime(id)} />
      <div className="content-wrapper">
        <Content data={data} />
        {attachments.map((path) => (
          <Attachment path={path} key={path} />
        ))}
      </div>
    </div>
  );
}
