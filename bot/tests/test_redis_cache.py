import pytest

from bot.common.cache import RedisCache
from bot.common.redis import get_new_redis


@pytest.mark.asyncio
async def test_cache_has_cache():
    cache: RedisCache = RedisCache(get_new_redis())
    exists = await cache.has_cache("does_not_exists")
    assert not exists

    await cache.cache_item("cache_test_has_cache", "123")
    exists = await cache.has_cache("cache_test_has_cache")
    assert exists


@pytest.mark.asyncio
async def test_cache_cache():
    cache: RedisCache = RedisCache(get_new_redis())
    await cache.redis.delete("cache_cache")

    result = await cache.cache_item("cache_cache", "123")
    assert result

    result = await cache.cache_item("cache_cache", "123")
    assert not result


@pytest.mark.asyncio
async def test_cache_max_size():
    cache: RedisCache = RedisCache(get_new_redis(), max_size=5)
    await cache.redis.delete("cache_max_size")

    for _ in range(20):
        await cache.cache_item("cache_max_size", str(_))

    data = await cache.redis.zrange("cache_max_size", 0, -1)
    assert len(data) == 5

    assert "19" in data
    assert "14" not in data
