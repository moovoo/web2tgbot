import asyncio
import json
import sys

from bot.common.crud import get_media_sources, get_conversations_for_media_source
from bot.common.models import ScrapSource
from bot.db.database import async_session


async def main():
    output = {}
    async with async_session() as db:
        sources = await get_media_sources(db)
        for source in sources:
            parsed = ScrapSource.from_str_tuple(source)
    
            conversations = await get_conversations_for_media_source(db, source)
            for conv in conversations:
                conversation_list = output.setdefault(parsed.to_url(), [])
                conversation_list.append(conv)
    json.dump(output, sys.stdout, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
