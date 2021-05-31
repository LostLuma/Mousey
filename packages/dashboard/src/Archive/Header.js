import React from "react";

import { formatIso8601Date, snowflakeTime } from "./utils";

import "./Header.css";

const MONTH = 86400 * 30 * 1000;

export default function Header({ id }) {
  const createdAt = snowflakeTime(id);

  const timestamp = createdAt.getTime();
  const expiresAt = new Date(timestamp + MONTH);

  return (
    <div className="archive-header">This archive expires on {formatIso8601Date(expiresAt)}.</div>
  );
}
