from functools import lru_cache
from logging import getLogger
from typing import Dict, List

from bot.common.crud import find_or_add_media_source, add_conversation_for_media_source, \
    delete_conversation_for_media_source, \
    get_conversations_for_media_source, get_media_sources, delete_media_source, get_media_sources_for_conversation, \
    get_conversation_settings
from bot.common.models import IncomingMessage, ScrapSource
from bot.common.settings import get_settings
from bot.db.database import async_session

logger = getLogger("config")


class ConfigurationError(Exception):
    pass


class TooManySubs(ConfigurationError):
    pass


class AbstractConfiguration:
    async def find_subs(self, source_id: str) -> List[str]:
        pass

    async def add_sub(self, scrap_source: ScrapSource, message: IncomingMessage) -> None:
        pass

    async def rm_sub(self, scrap_source: ScrapSource, message: IncomingMessage) -> None:
        pass

    async def get_sources(self) -> List[str]:
        pass

    async def find_sources(self, conversation_id: str) -> List[str]:
        pass

    async def get_conversation_settings(self, conversation_id: str) -> Dict[str, str]:
        pass

    @staticmethod
    def parse_subs(items: List[str]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for item in items:
            provider, conversation_id = item.split("@")
            result.setdefault(provider, []).append(conversation_id)
        return result

class PGConfiguration(AbstractConfiguration):

    def __init__(self):
        self.logger = getLogger()

    async def find_subs(self, source_id: str) -> List[str]:
        async with async_session() as db:
            items = await get_conversations_for_media_source(db, source_id)
            self.logger.debug("Found subs for %s %s", source_id, items)
            return items

    async def add_sub(self, scrap_source: ScrapSource, message: IncomingMessage) -> None:
        self.logger.debug("Adding new sub %s, %s %s", scrap_source.to_str_tuple(), message.provider,
                          message.conversation_id)
        conv_id = f"{message.provider}@{message.conversation_id}"
        async with async_session() as db:
            existing = await get_media_sources_for_conversation(db, conv_id)
            if len(existing) > get_settings().max_sources:
                raise TooManySubs()

            source = await find_or_add_media_source(db, scrap_source.to_str_tuple())
            await add_conversation_for_media_source(db, conv_id, source)

    async def rm_sub(self, scrap_source: ScrapSource, message: IncomingMessage) -> None:
        self.logger.debug("Removing sub %s, %s %s", scrap_source.to_str_tuple(), message.provider,
                          message.conversation_id)

        full_id = scrap_source.to_str_tuple()
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
            return await get_media_sources_for_conversation(db, conversation_id)\

    async def get_conversation_settings(self, conversation_id: str) -> Dict[str, str]:
        async with async_session() as db:
            item = await get_conversation_settings(db, conversation_id)
            if item is None:
                return {}
            else:
                return {
                    "filter": item.filter,
                }

@lru_cache
def get_configuration() -> AbstractConfiguration:
    return PGConfiguration()
