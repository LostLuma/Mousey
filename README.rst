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

Development
-----------

The bot uses custom events in addition to the ones provided by Discord, you can identify these
by the ``mouse_`` prefix and find where they are defined by searching the project for the name.

If you'd like to contribute changes please test them locally first, you can do so pretty easily using Docker:

- Create an ``.env`` file with your configuration in the relevant package directory
- To run the API run ``docker-compose -f docker-compose.yaml -f docker-compose-dev.yaml up`` in ``packages/api``
- Running the bot also requires starting the the API, then you can run ``docker-compose up`` in ``packages/bot``
