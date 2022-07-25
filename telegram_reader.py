import asyncio
import logging.config
import os
from logging import getLogger

from common.pubsub import Pubsub, get_new_pubsub
from telegram.telegram_models import Message
from telegram.updates import TelegramUpdates
from common.models import IncomingMessage


class TelegramMessagePublisher:

    def __init__(self, tg_bot_token: str):
        self.token = tg_bot_token
        self.bot_id = tg_bot_token.split(":")[0]
        self.tg_updates = TelegramUpdates(self.token)

        self.pubsub: Pubsub = get_new_pubsub()

        self.logger = getLogger("TGPublisher")

    async def serve(self):
        async for update in self.tg_updates.iter_updates():
            self.logger.debug(f"Got update {update}")
            if update.message and update.message.text:
                await self.process_message(update.message)
            elif update.channel_post and update.channel_post.text:
                await self.process_message(update.channel_post)

    async def process_message(self, message: Message):
        ch = "incoming_message"
        msg = IncomingMessage(provider=f"telegram_{self.bot_id}",
                              conversation_id=str(message.chat.id),
                              from_user_id=str(message.from_user.id) if message.from_user else "",
                              payload=message.text,
                              message_id=message.message_id)
        self.logger.debug(f"Going to send {msg} to {ch}")
        await self.pubsub.publish(ch, msg.json())


async def main():
    token = os.getenv("TG_BOT_TOKEN")
    publisher = TelegramMessagePublisher(token)
    await publisher.serve()


if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    asyncio.run(main())
