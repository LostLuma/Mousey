const DISCORD_EPOCH = BigInt("1420070400000");

export function snowflakeTime(value) {
  const snowflake = BigInt(value);
  const timestamp = (snowflake >> BigInt("22")) + DISCORD_EPOCH;

  return new Date(Number(timestamp));
}

export function formatIso8601Date(date) {
  function pad(number) {
    return number.toString().padStart(2, "0");
  }

  const year = [date.getFullYear(), date.getMonth() + 1, date.getDate()];
  const hour = [date.getHours(), date.getMinutes(), date.getSeconds()];

  return year.map(pad).join("-") + " " + hour.map(pad).join(":");
}
