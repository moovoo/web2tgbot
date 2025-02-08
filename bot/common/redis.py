from redis.asyncio import Redis

from bot.common.settings import get_settings


def get_new_redis():
    return Redis.from_url(get_settings().redis, decode_responses=True)
