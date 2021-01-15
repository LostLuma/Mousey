======
Mousey
======

Mousey is a WIP moderation and utility bot for Discord.

You may `invite the official instance <https://mousey.app/invite>`_ to your server, or self-host the bot.

TODO
----

A non-exhaustive and unordered list of things I still need to do.

Some of these things already exist in the old version of the bot and I haven't gotten around to adding them here.

- Spam protection
- Tags / Custom commands
- Recreate / Update emoji API for blobs.gg etc.
- Log changes to guilds (verification level, description, etc.)
- Case-insensitive converters for non-moderation commands
- Ban sync (needed for BE)
- Save moderation history
- Self-assignable roles

Development
-----------

The bot uses custom events in addition to the ones provided by Discord, you can identify these
by the ``mouse_`` prefix and find where they are defined by searching the project for the name.

If you'd like to contribute changes please test them locally first, you can do so by creating an ``.env`` file
with your configuration and then run ``docker-compose up`` in the project directory to run the bot. Thank you!
