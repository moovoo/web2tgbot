import os

import aioredis


def get_new_redis():
    return aioredis.from_url(os.getenv("REDIS", "redis://localhost/"), decode_responses=True)
