import React from "react";

import "./Author.css";

export default function Author({ user }) {
  return (
    <>
      <div className="author">
        {user.name}
        <div className="discriminator">#{user.discriminator}</div>
      </div>
    </>
  );
}
