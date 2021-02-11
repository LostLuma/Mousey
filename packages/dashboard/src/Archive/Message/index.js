import React from "react";

import { snowflakeTime } from "../utils";
import Attachment from "./Attachment";
import Author from "./Author";
import Avatar from "./Avatar";
import Content from "./Content";
import Timestamp from "./Timestamp";

import "./index.css";

export default function Message({ data }) {
  const { attachments, author, channel, embeds, id } = data;

  return (
    <div className="message">
      <Avatar user={author} />
      <Author user={author} />
      <Timestamp date={snowflakeTime(id)} />
      <div className="content-wrapper">
        <div className="inner-content">
          <Content data={data} />
          {attachments.map((path) => (
            <Attachment path={path} key={path} />
          ))}
        </div>
      </div>
    </div>
  );
}
