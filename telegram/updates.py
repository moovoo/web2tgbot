import asyncio
from typing import List, AsyncIterable

import aiohttp
from pydantic import parse_obj_as, parse_raw_as
from logging import getLogger
from .telegram_models import Update, BOT_URL, TelegramReply, GetUpdates, TelegramException


class TelegramUpdates:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.logger = getLogger(__name__)

    async def iter_updates(self) -> AsyncIterable[Update]:
        url = BOT_URL + self.bot_token + "/getUpdates"
        get_updates_query = GetUpdates()
        get_updates_query.timeout = 60
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.post(url, json=get_updates_query.dict(exclude_unset=True)) as request:
                        self.logger.debug(f"Got updates reply {request.status}")
                        raw = await request.read()
                        reply: TelegramReply = parse_raw_as(TelegramReply, raw)
                        if not reply.ok:
                            raise TelegramException(f"Telegram update failure {reply.error_code}: {reply.description}")

                        updates = parse_obj_as(List[Update], reply.result)

                        for update in updates:
                            yield update
                            get_updates_query.offset = update.update_id + 1

                except asyncio.exceptions.TimeoutError:
                    self.logger.exception("Timeout")
                    await asyncio.sleep(5)

                except aiohttp.ClientError:
                    self.logger.exception("Failed to get new update")
                    await asyncio.sleep(5)
