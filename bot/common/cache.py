from redis.asyncio import Redis
import time

from bot.common.redis import get_new_redis


class Cache:
    async def cache_item(self, cache_name: str, item: str) -> bool:
        pass

    async def has_cache(self, cache_name: str) -> bool:
        pass

    async def store_item(self, key: str, value: str):
        pass

    async def get_item(self, key: str) -> str:
        pass

class RedisCache(Cache):
    def __init__(self, redis: Redis, max_size: int = 500, expiration: int = 30*24*60*60):
        self.redis = redis
        self.max_size = max_size
        self.expiration = expiration

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
        await self.redis.expire(cache_name, self.expiration)

    async def store_item(self, key: str, value: str):
        await self.redis.set(key, value)

    async def get_item(self, key: str) -> str:
        return await self.redis.get(key)

def get_new_cache() -> Cache:
    return RedisCache(get_new_redis())
