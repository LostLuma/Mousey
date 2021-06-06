import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import Header from "./Header";
import Message from "./Message";

export default function Archive() {
  const { id } = useParams();
  const [data, setData] = useState();

  useEffect(() => {
    if (!/^\d{15,21}$/u.exec(id)) {
      setData({ error: "Invalid archive ID specified." });
      return;
    }

    async function fetchData() {
      let resp;

      try {
        resp = await fetch(`https://api.mousey.app/v4/archives/${id}`);
      } catch {
        setData({ error: "Failed to fetch archive data." });
        return;
      }

      const data = await resp.json();

      if (resp.ok) {
        setData(data);
      } else {
        setData({ error: data.error });
      }
    }
    fetchData();
  }, [id]);

  if (!data) {
    return <div className="status">Loading archive ...</div>;
  } else if (data.error) {
    return <div className="status error">{data.error}</div>;
  }

  const messages = data.messages;
  messages.sort((a, b) => (a.id > b.id ? 1 : -1));

  const onCopy = (event) => {
    const selection = document.getSelection();
    const re = /(.{2,32}#\d{4})\s{1,2}(\d{4}(?:-\d{2}){2}\s(?:\d{2}:){2}\d{2})/gm
    const output = selection.toString().replaceAll(re, "$1 $2")

    event.clipboardData.setData('text/plain', output);
    event.preventDefault();
  }

  return (
    <>
      <Header id={id} />
      <div className="messages" onCopy={onCopy}>
        {messages.map((message) => (
          <Message data={message} key={message.id} />
        ))}
      </div>
    </>
  );
}
