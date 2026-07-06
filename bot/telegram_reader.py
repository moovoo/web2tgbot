import asyncio
import logging.config
import os
from logging import getLogger

from bot.common.pubsub import Pubsub, get_new_pubsub
from bot.common.settings import get_settings
from bot.common.models import IncomingMessage

from prometheus_client import Counter
from prometheus_async.aio import web

import telegram

class UpdateReader:

    READER_INCOMING_MESSAGES_PROCESSED = Counter(
        "tg_reader_incoming_messages_processed",
        documentation="Number of incoming messages processed by telegram reader",
        labelnames=["conversation_id", "from_user_id"],)

    def __init__(self, tg_bot_token: str):
        self.token = tg_bot_token
        self.bot_id = tg_bot_token.split(":")[0]
        # self.tg_updates = TelegramUpdates(self.token)
        self.bot = telegram.Bot(self.token)
        self.pubsub: Pubsub = get_new_pubsub()

        self.logger = getLogger("UpdateReader")

    async def serve(self):
        async with self.bot:
            updates = (await self.bot.get_updates())
            self.logger.debug(f"Got update {updates}")
            for update in updates:
                if update.message and update.message.text:
                    await self.process_message(update.message)
                elif update.channel_post and update.channel_post.text:
                    await self.process_message(update.channel_post)

    async def process_message(self, message: telegram.Message):
        ch = "incoming_message"
        msg = IncomingMessage(provider=f"telegram_{self.bot_id}",
                              conversation_id=str(message.chat.id),
                              from_user_id=str(message.from_user.id) if message.from_user else "",
                              payload=message.text or "",
                              message_id=str(message.message_id))
        self.logger.debug(f"Going to send {msg} to {ch}")
        self.READER_INCOMING_MESSAGES_PROCESSED.labels(
            conversation_id=msg.conversation_id,
            from_user_id=msg.from_user_id).inc()
        await self.pubsub.publish(ch, msg.model_dump_json())


async def main():
    _ = await web.start_http_server(port=8000)
    token = get_settings().bot_token
    publisher = UpdateReader(token)
    await publisher.serve()


if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    asyncio.run(main())
