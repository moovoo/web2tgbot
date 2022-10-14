import asyncio
import json
import os
import sys

from bot.common.crud import find_or_add_media_source, add_conversation_for_media_source
from bot.db.database import async_session
from bot.scrap.reddit_models import SubredditListing


async def main(file):
    data = json.load(file)
    async with async_session() as db:
        for media_source, convs in data.items():
            print(f"Adding source {media_source}, convs: {convs}")
            # todo: non reddit stuff
            listing = SubredditListing.from_url(media_source)
            src = await find_or_add_media_source(db, "reddit@" + listing.to_str_tuple())

            for conv in convs:
                await add_conversation_for_media_source(db, conv, src)

if __name__ == "__main__":
    asyncio.run(main(sys.stdin))
