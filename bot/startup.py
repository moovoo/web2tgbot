import asyncio

import aio_pika
import aioredis

from bot.common.settings import get_settings
from bot.db.database import async_session


async def wait_db():
    while True:
        try:
            async with async_session() as db:
                await db.execute("select * from alembic_version")
            print("DB is ok")
            break
        except Exception as ex:
            print(f"DB is down: {ex}")
        await asyncio.sleep(1)


async def wait_rmq():
    while True:
        try:
            await aio_pika.connect_robust(get_settings().rabbitmq)
            print("RMQ is ok")
            break
        except Exception as ex:
            print(f"RMQ is down: {ex}")
        await asyncio.sleep(1)


async def wait_redis():
    c = aioredis.from_url(get_settings().redis)
    while True:
        try:
            await c.ping()
            print("Redis is ok")
            break
        except Exception as ex:
            print(f"Redis is down: {ex}")
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(wait_db(), wait_rmq(), wait_redis())

if __name__ == "__main__":
    asyncio.run(main())
