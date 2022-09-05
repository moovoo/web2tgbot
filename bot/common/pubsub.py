import asyncio
from logging import getLogger
from typing import Any, Tuple, AsyncGenerator

import aio_pika
import aioredis
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel, AbstractIncomingMessage

from bot.common.redis import get_new_redis
from bot.common.settings import get_settings


class Pubsub:
    async def publish(self, channel_id: str, message: str | bytes) -> None:
        pass

    def stream_messages(self, *args) -> AsyncGenerator[Tuple[str, str | None, str], Any]:
        pass

    async def ack_message(self, channel_id: str, message_id: str) -> None:
        pass


class PubsubRedis(Pubsub):
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis
        self.pubsub = self.redis.pubsub()
        self.logger = getLogger("PBRedis")

    async def publish(self, channel_id: str, message: str | bytes, verify_accepted: bool = False) -> None:
        to_sleep = 0
        while True:
            res = await self.redis.publish(channel_id, message)
            if not verify_accepted or res:
                break
            self.logger.warning(f"No one accepted a message for channel {channel_id}")
            to_sleep += 1 if to_sleep < 30 else 0
            await asyncio.sleep(to_sleep)

    async def stream_messages(self, *args) -> AsyncGenerator[Tuple[str, str | None, str], Any]:
        await self.pubsub.subscribe(*args)
        try:
            while True:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                if not message:
                    continue
                # {'type': 'message', 'pattern': None, 'channel': 'ch3', 'data': '1551515'}
                if message.get("type") == "message":
                    stop = yield message.get("channel"), None, message.get("data")
                    if stop:
                        break

        finally:
            await self.pubsub.unsubscribe(args)


class PubsubRabbitmq(Pubsub):

    def __init__(self):
        self.connection: AbstractRobustConnection | None = None
        self.channel: AbstractRobustChannel | None = None

    async def _get_connection(self):
        if self.connection is None:
            self.connection = await aio_pika.connect_robust(get_settings().rabbitmq)
            self.channel = await self.connection.channel()
        else:
            await self.connection.ready()

    async def publish(self, channel_id: str, message: str | bytes) -> None:
        await self._get_connection()
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=message if type(message) is bytes else message.encode()
            ), routing_key=channel_id)

    async def stream_messages(self, *args) -> AsyncGenerator[Tuple[str, str | None, str], Any]:
        await self._get_connection()
        # await self.channel.basic_qos(prefetch_count=1)

        queue = asyncio.Queue()

        async def callback(msg: AbstractIncomingMessage):
            await queue.put(msg)
            print(await msg.ack())

        for queue_name in args:
            q = await self.channel.declare_queue(queue_name, durable=True)
            await q.consume(callback, no_ack=True)

        while True:
            message: AbstractIncomingMessage = await queue.get()
            stop = yield message.routing_key, message.delivery_tag, message.body
            if stop:
                break


def get_new_pubsub() -> Pubsub:
    return PubsubRabbitmq()
