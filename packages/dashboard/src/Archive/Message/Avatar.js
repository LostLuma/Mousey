import React from "react";

import "./Avatar.css";

const DISCORD_CDN = "https://cdn.discordapp.com";

export default function Avatar({ user }) {
  let image;

  if (!user.avatar) {
    const id = user.discriminator % 5;
    const path = `/embed/avatars/${id}.png?size=128`;

    image = <img src={DISCORD_CDN + path} alt="default avatar" loading="lazy" />;
  } else {
    const path = `/avatars/${user.id}/${user.avatar}`;

    image = (
      <>
        <source srcSet={DISCORD_CDN + path + ".webp?size=128"} type="image/webp" />
        <img src={DISCORD_CDN + path + ".png?size=128"} alt="avatar" loading="lazy" />
      </>
    );
  }

  return (
    <div className="avatar">
      <picture>{image}</picture>
    </div>
  );
}
