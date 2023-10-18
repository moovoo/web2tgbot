import asyncio
import logging.config
from typing import List

from pydantic import parse_raw_as
from logging import getLogger

from bot.common.configuration import get_configuration, TooManySubs
from bot.common.models import IncomingMessage, Post, OutboundMessage
from bot.common.pubsub import get_new_pubsub
from bot.common.redis import get_new_redis
from bot.scrap.reddit_models import SubredditListing, BadRedditUrlException


class Web2TgBot:
    def __init__(self):
        self.pubsub = get_new_pubsub()
        self.redis = get_new_redis()
        self.logger = getLogger()
        self.configuration = get_configuration()

    async def serve(self):
        pubsub = get_new_pubsub()
        reader = pubsub.stream_messages("incoming_message", "media")
        async for channel_id, message_id, message_raw in reader:
            if channel_id == "media":
                post: Post = parse_raw_as(Post, message_raw)
                self.logger.debug("Got new post %s", post)

                await self.process_post(post)

            elif channel_id == "incoming_message":
                message: IncomingMessage = parse_raw_as(IncomingMessage, message_raw)
                self.logger.debug("Got incoming message %s", message)

                await self.process_incoming_message(message)

            await self.pubsub.ack_message(channel_id, message_id)

    async def send_message(self, dest: str,  conversations: List[str], *,
                           post: Post | None = None, text: str | None = None):
        self.logger.debug("Will send %s to %s: %s", post or text, dest, conversations)
        await self.pubsub.publish(dest, OutboundMessage(post=post, text=text, conversation_ids=conversations).json())

    async def process_post(self, post: Post):
        destinations = await self.configuration.find_subs(post.source_id)
        for dest, convs in destinations.items():
            await self.send_message(dest, convs, post=post)

    async def process_incoming_message(self, message: IncomingMessage):
        if message.payload.startswith("/start "):
            dest = message.payload[len("/start "):].strip()
            try:
                listing = SubredditListing.from_url(dest)
                await self.configuration.add_reddit_sub(listing, message)
            except BadRedditUrlException:
                self.logger.warning("Tried to start bad reddit %s %s", dest, message.conversation_id)
                await self.send_message(message.provider, conversations=[message.conversation_id],
                                        text="Bad reddit listing URL")
                return
            except TooManySubs:
                await self.send_message(message.provider, conversations=[message.conversation_id],
                                        text="Too many subscriptions")

        elif message.payload.startswith("/stop "):
            dest = message.payload[len("/stop "):].strip()
            try:
                listing = SubredditListing.from_url(dest)
            except BadRedditUrlException:
                self.logger.warning("Tried to stop bad reddit %s %s", dest, message.conversation_id)
                await self.send_message(message.provider, conversations=[message.conversation_id],
                                        text="Bad reddit listing URL")
                return
            await self.configuration.rm_reddit_sub(listing, message)
        elif message.payload.startswith("/list"):
            sources = await self.configuration.find_sources(message.provider + "@" + message.conversation_id)
            if sources:
                reply_text = "Subs: \n\n" + \
                             "\n".join((SubredditListing.from_str_tuple(src.split("@")[1]).to_url() for src in sources))
            else:
                reply_text = "Nothing found"
            await self.send_message(message.provider, conversations=[message.conversation_id],
                                    text=reply_text)


async def main():
    await Web2TgBot().serve()

if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    asyncio.run(main())
