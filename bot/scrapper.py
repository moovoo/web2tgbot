import asyncio
import logging.config
import sys
from logging import getLogger
from typing import List
from prometheus_async.aio import web
from prometheus_client import Counter, Gauge

from bot.common.cache import get_new_cache
from bot.common.configuration import get_configuration
from bot.common.models import ScrapSource, BadSourceException, ScrapSourceType, Post
from bot.common.pubsub import get_new_pubsub
from bot.common.redis import get_new_redis
from bot.common.settings import get_settings
from bot.scrap.insta import InstaPosts
from bot.scrap.reddit import RedditPosts, RedditHttpProvider
from bot.scrap.basescrapper import BaseScrapper, ScrapValidationError, ScrapNotFoundError, ScrapThrottleError, \
    ScrapError, BaseHttpProvider

logger = getLogger()

async def main(scrap_source_name: str):
    _ = await web.start_http_server(port=8000)

    scrap_source_type = ScrapSourceType(scrap_source_name)

    redis = get_new_redis()
    pubsub = get_new_pubsub()
    cache = get_new_cache()
    configuration = get_configuration()

    match scrap_source_type:
        case ScrapSourceType.Reddit:
            provider = RedditHttpProvider()
            posts: BaseScrapper = RedditPosts(provider)
        case ScrapSourceType.Instagram:
            provider = BaseHttpProvider()
            posts: BaseScrapper = InstaPosts(cache, provider)
        case _:
            raise Exception("Can't scrap that source")

    posts_pushed = Counter(f"{scrap_source_type.value}_posts_pushed", "Number of posts pushed", labelnames=["sub"])
    scrap_pause = Gauge(f"{scrap_source_type.value}_scrap_pause", "Time between requests", labelnames=["sub"])

    max_pause = posts.max_pause
    default_pause = posts.default_pause
    pause = default_pause

    await posts.start()
    try:
        while True:
            watch_subs: List[str] = await configuration.get_sources()
            for full_id in watch_subs:
                try:
                    sub = ScrapSource.from_str_tuple(full_id)
                    if sub.source_type != scrap_source_type:
                        continue
                except BadSourceException:
                    logger.warning("Can't parse scrap source %s", full_id)
                    continue

                cache_name = f"cache_{sub.params.to_str_tuple()}"
                first_time = not await cache.has_cache(cache_name)

                scrapped: List[Post] = []
                while True:
                    scrap_pause.labels(sub=sub.to_str_tuple()).set(pause)
                    await asyncio.sleep(pause)
                    try:
                        scrapped = await posts.get_posts(sub)
                    except ScrapNotFoundError:
                        logger.warning("Could not found listing, ignoring...")
                    except ScrapValidationError:
                        logger.error("Validation failed")
                    except ScrapThrottleError:
                        pause += 30 if pause < max_pause else 0
                        logger.warning("Too many requests %s, will wait for %s", sub.params.to_str_tuple(), pause)
                        continue
                    except ScrapError:
                        logger.exception("Failed to get posts %s", sub.params.to_str_tuple())
                    break

                pause = default_pause

                for post in scrapped:
                    if await cache.cache_item(cache_name, post.unique_id) and not first_time:
                        await posts.download_media([post], get_settings().media_path)
                        posts_pushed.labels(sub=sub.params.to_str_tuple()).inc()
                        logger.debug("Going to send new post: %s", post)
                        await pubsub.publish("media",
                                              post.model_dump_json(exclude_unset=True, exclude_defaults=True, exclude_none=True))
            await asyncio.sleep(1)
    finally:
        await posts.stop()

if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    try:
        src = sys.argv[1]
    except IndexError:
        src = "reddit"
    asyncio.run(main(src))
