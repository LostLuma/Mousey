import React from "react";

import { formatIso8601Date } from "../utils";

import "./Timestamp.css";

export default function Timestamp({ date }) {
  return <div className="timestamp">{formatIso8601Date(date)}</div>;
}
