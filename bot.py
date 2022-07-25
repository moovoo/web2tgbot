import asyncio
import logging.config
from typing import List, Dict

from pydantic import parse_raw_as
from logging import getLogger

from common.models import IncomingMessage, Post, OutboundMessage
from common.pubsub import get_new_pubsub
from common.redis import get_new_redis
from scrap.reddit_models import SubredditListing, BadRedditUrlException


class Web2TgBot:
    def __init__(self):
        self.pubsub = get_new_pubsub()
        self.redis = get_new_redis()
        self.logger = getLogger()

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

    async def process_post(self, post: Post):
        destinations = await self.find_subs(post.source_id)
        for dest, convs in destinations.items():
            self.logger.debug("Will send post from %s to %s: %s", post.source_id, dest, convs)
            await self.pubsub.publish(dest, OutboundMessage(post=post, conversation_ids=convs).json())

    async def process_incoming_message(self, message: IncomingMessage):
        if message.payload.startswith("/start "):
            dest = message.payload[len("/start "):].strip()
            try:
                listing = SubredditListing.from_url(dest)
                await self.add_reddit_sub(listing, message)
            except BadRedditUrlException:
                pass  # todo: error message
        elif message.payload.startswith("/stop "):
            dest = message.payload[len("/stop "):].strip()
            try:
                listing = SubredditListing.from_url(dest)
                await self.rm_reddit_sub(listing, message)
            except BadRedditUrlException:
                pass  # todo: error message

    async def find_subs(self, source_id: str) -> Dict[str, List[str]]:
        items: List[str] = await self.redis.smembers(f"subs_{source_id}")
        result: Dict[str, List[str]] = {}
        for item in items:
            provider, conversation_id = item.split("@")
            result.setdefault(provider, []).append(conversation_id)
        return result

    async def add_reddit_sub(self, listing: SubredditListing, message: IncomingMessage):
        self.logger.debug("Adding new reddit sub %s, %s %s", listing.to_str_tuple(), message.provider, message.conversation_id)
        await self.redis.sadd("reddit_listings", listing.to_str_tuple())
        await self.redis.sadd(f"subs_reddit@{listing.to_str_tuple()}", f"{message.provider}@{message.conversation_id}")

    async def rm_reddit_sub(self, listing: SubredditListing, message: IncomingMessage):
        self.logger.debug("Removing reddit sub %s, %s %s", listing.to_str_tuple(), message.provider, message.conversation_id)
        await self.redis.srem("reddit_listings", listing.to_str_tuple())
        await self.redis.srem(f"subs_reddit@{listing.to_str_tuple()}", f"{message.provider}@{message.conversation_id}")


async def main():
    await Web2TgBot().serve()

if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    asyncio.run(main())
