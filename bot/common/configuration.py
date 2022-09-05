from functools import lru_cache
from logging import getLogger
from typing import Dict, List

from bot.common.crud import find_or_add_media_source, add_conversation_for_media_source, \
    delete_conversation_for_media_source, \
    get_conversations_for_media_source, get_media_sources, delete_media_source, get_media_sources_for_conversation
from bot.common.models import IncomingMessage
from bot.common.settings import get_settings
from bot.db.database import async_session
from bot.scrap.reddit_models import SubredditListing

logger = getLogger("config")


class ConfigurationError(Exception):
    pass


class TooManySubs(ConfigurationError):
    pass


class AbstractConfiguration:
    async def find_subs(self, source_id: str) -> Dict[str, List[str]]:
        pass

    async def add_reddit_sub(self, listing: SubredditListing, message: IncomingMessage) -> None:
        pass

    async def rm_reddit_sub(self, listing: SubredditListing, message: IncomingMessage) -> None:
        pass

    async def get_sources(self) -> List[str]:
        pass

    async def find_sources(self, conversation_id: str) -> List[str]:
        pass


class PGConfiguration(AbstractConfiguration):

    def __init__(self):
        self.logger = getLogger()

    async def find_subs(self, source_id: str) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        async with async_session() as db:
            items = await get_conversations_for_media_source(db, source_id)
            self.logger.debug("Found subs for %s %s", source_id, items)
            for item in items:
                provider, conversation_id = item.split("@")
                result.setdefault(provider, []).append(conversation_id)
        return result

    async def add_reddit_sub(self, listing: SubredditListing, message: IncomingMessage) -> None:
        self.logger.debug("Adding new reddit sub %s, %s %s", listing.to_str_tuple(), message.provider,
                          message.conversation_id)
        conv_id = f"{message.provider}@{message.conversation_id}"
        async with async_session() as db:
            existing = await get_media_sources_for_conversation(db, conv_id)
            if len(existing) > get_settings().max_sources:
                raise TooManySubs()

            source = await find_or_add_media_source(db, "reddit@" + listing.to_str_tuple())
            await add_conversation_for_media_source(db, conv_id, source)

    async def rm_reddit_sub(self, listing: SubredditListing, message: IncomingMessage) -> None:
        self.logger.debug("Removing reddit sub %s, %s %s", listing.to_str_tuple(), message.provider,
                          message.conversation_id)

        full_id = "reddit@" + listing.to_str_tuple()
        async with async_session() as db:
            await delete_conversation_for_media_source(
                db,
                full_id,
                f"{message.provider}@{message.conversation_id}"
            )

            if not await get_conversations_for_media_source(db, full_id):
                await delete_media_source(db, full_id)

    async def get_sources(self) -> List[str]:
        async with async_session() as db:
            return await get_media_sources(db)

    async def find_sources(self, conversation_id: str) -> List[str]:
        async with async_session() as db:
            return await get_media_sources_for_conversation(db, conversation_id)


@lru_cache
def get_configuration() -> AbstractConfiguration:
    return PGConfiguration()
