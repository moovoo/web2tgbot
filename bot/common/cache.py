from aioredis import Redis
import time

from bot.common.redis import get_new_redis


class Cache:
    async def cache_item(self, cache_name: str, item: str) -> bool:
        pass

    async def has_cache(self, cache_name: str) -> bool:
        pass


class RedisCache(Cache):
    def __init__(self, redis: Redis, max_size: int = 500):
        self.redis = redis
        self.max_size = max_size

    async def cache_item(self, cache_name: str, item: str) -> bool:
        result = await self.redis.zadd(cache_name, mapping={item: time.time()})
        await self.strip(cache_name)  # todo: run it once in a while?
        return result > 0

    async def has_cache(self, cache_name: str) -> bool:
        return await self.redis.exists(cache_name) > 0

    async def strip(self, cache_name: str):
        # todo: redis func
        sz = await self.redis.zcard(cache_name)
        if sz > self.max_size:
            await self.redis.zpopmin(cache_name, sz - self.max_size)
        await self.redis.expire(cache_name, 30*24*60*60)


def get_new_cache() -> Cache:
    return RedisCache(get_new_redis())
