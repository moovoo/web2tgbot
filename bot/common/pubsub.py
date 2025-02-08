import asyncio
from typing import Any, Tuple, AsyncGenerator

import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel, AbstractIncomingMessage

from bot.common.settings import get_settings


class Pubsub:
    async def publish(self, channel_id: str, message: str | bytes) -> None:
        pass

    def stream_messages(self, *args) -> AsyncGenerator[Tuple[str | None, int | None, bytes], Any]:
        pass

    async def ack_message(self, channel_id: str, message_id: int) -> None:
        pass


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

    async def stream_messages(self, *args) -> AsyncGenerator[Tuple[str | None, int | None, bytes], Any]:
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
