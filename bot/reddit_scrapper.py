import asyncio
import logging.config
from logging import getLogger
from typing import List

from bot.common.cache import get_new_cache
from bot.common.configuration import get_configuration
from bot.common.pubsub import get_new_pubsub
from bot.common.redis import get_new_redis
from bot.scrap.reddit import RedditPosts, RedditError, RedditThrottleError, reddit_post_to_message
from bot.scrap.reddit_models import SubredditListing, BadRedditUrlException

logger = getLogger()


async def main():
    redis = get_new_redis()
    pubsub = get_new_pubsub()
    cache = get_new_cache()
    configuration = get_configuration()

    rd_posts = RedditPosts()

    default_pause = 10.0
    pause = default_pause

    while True:
        watch_subs: List[str] = await configuration.get_sources()
        for full_id in watch_subs:
            try:
                sub_type, sub_name = full_id.split("@")
                if sub_type != "reddit":
                    continue
                sub = SubredditListing.from_str_tuple(sub_name)
            except BadRedditUrlException:
                logger.warning("Not a reddit listing %s", full_id)
                continue
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
                    post = reddit_post_to_message(full_id, reddit_post.data)
                    logger.debug("Going to send new post: %s", post)
                    await pubsub.publish("media",
                                         post.json(exclude_unset=True, exclude_defaults=True, exclude_none=True))
        await asyncio.sleep(1)

if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    asyncio.run(main())
