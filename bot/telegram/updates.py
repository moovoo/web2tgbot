import asyncio
from typing import List, AsyncIterable

import aiohttp
from pydantic import TypeAdapter
from logging import getLogger
from .telegram_models import Update, TelegramReply, GetUpdates, TelegramException
from ..common.settings import get_settings

from prometheus_client import Counter

class TelegramUpdates:

    TG_UPDATES_ERRORS = Counter(name='tg_updates_error', documentation="Telegram updates error",
                               labelnames=["error_type"])
    TG_UPDATES = Counter(name='tg_updates', documentation="Telegram updates count",)

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.logger = getLogger(__name__)

    async def iter_updates(self) -> AsyncIterable[Update]:
        url = get_settings().BOT_URL + self.bot_token + "/getUpdates"
        get_updates_query = GetUpdates()
        get_updates_query.timeout = 60
        adapter = TypeAdapter(List[Update])
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.post(url, json=get_updates_query.model_dump(exclude_unset=True)) as request:
                        self.logger.debug(f"Got updates reply {request.status}")
                        raw = await request.read()
                        reply: TelegramReply = TelegramReply.model_validate_json(raw)
                        if not reply.ok:
                            self.TG_UPDATES_ERRORS.labels(error_type=f"server_error_{reply.error_code}").inc()
                            raise TelegramException(f"Telegram update failure {reply.error_code}: {reply.description}")
                        updates = adapter.validate_python(reply.result)

                        self.TG_UPDATES.inc(len(updates))
                        for update in updates:
                            yield update
                            get_updates_query.offset = update.update_id + 1

                except asyncio.exceptions.TimeoutError:
                    self.logger.exception("Timeout")
                    self.TG_UPDATES_ERRORS.labels(error_type="timeout_error").inc()
                    await asyncio.sleep(5)

                except aiohttp.ClientError as ex:
                    self.logger.exception("Failed to get new update")
                    self.TG_UPDATES_ERRORS.labels(error_type=f"http_client_error_{ex.__class__.__name__.lower()}").inc()
                    await asyncio.sleep(5)
