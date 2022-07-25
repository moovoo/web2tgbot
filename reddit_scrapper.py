import asyncio
import logging.config
from logging import getLogger
from typing import List

from common.cache import get_new_cache
from common.pubsub import get_new_pubsub
from common.redis import get_new_redis
from scrap.reddit import RedditPosts, RedditError, RedditThrottleError, reddit_post_to_message
from scrap.reddit_models import SubredditListing

logger = getLogger()


async def main():
    redis = get_new_redis()
    pubsub = get_new_pubsub()
    cache = get_new_cache()

    rd_posts = RedditPosts()

    default_pause = 10.0
    pause = default_pause

    while True:
        watch_subs: List[str] = await redis.smembers("reddit_listings")
        for sub_name in watch_subs:

            sub = SubredditListing.from_str_tuple(sub_name)
            cache_name = f"cache_{sub_name}"
            first_time = not await cache.has_cache(cache_name)

            while True:
                await asyncio.sleep(pause)
                try:
                    posts = await rd_posts.get_posts(sub)
                    break
                except RedditThrottleError:
                    pause += 10 if pause < 300 else 0
                    logger.warning("Too many requests %s, will wait for %s", sub_name, pause)
                except RedditError:
                    logger.exception("Failed to get posts %s", sub_name)

            pause = default_pause

            for reddit_post in posts:
                if await cache.cache_item(cache_name, reddit_post.data.id) and not first_time:
                    post = reddit_post_to_message(f"reddit@{sub_name}", reddit_post.data)
                    logger.debug("Going to send new post: %s", post)
                    await pubsub.publish("media",
                                         post.json(exclude_unset=True, exclude_defaults=True, exclude_none=True))
        await asyncio.sleep(1)

if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    asyncio.run(main())
