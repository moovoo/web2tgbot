import asyncio
import json
import sys

from bot.common.crud import get_media_sources, get_conversations_for_media_source
from bot.db.database import async_session
from bot.scrap.reddit_models import SubredditListing


async def main():
    output = {}
    async with async_session() as db:
        sources = await get_media_sources(db)
        for source in sources:
            provider, source_name = source.split("@")
            # todo: non reddit sources?
            listing = SubredditListing.from_str_tuple(source_name)
    
            conversations = await get_conversations_for_media_source(db, source)
            for conv in conversations:
                conversation_list = output.setdefault(listing.to_url(), [])
                conversation_list.append(conv)
    json.dump(output, sys.stdout, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
