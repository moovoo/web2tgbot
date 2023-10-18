import os

import aioredis

from bot.common.settings import get_settings


def get_new_redis():
    return aioredis.from_url(get_settings().redis, decode_responses=True)
