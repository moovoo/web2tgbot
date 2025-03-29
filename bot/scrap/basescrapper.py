import asyncio
import random
import time
from logging import getLogger
from typing import List, Counter

import aiohttp
from fake_useragent import UserAgent
from prometheus_client import Histogram

from bot.common.models import ScrapSource, Post

class ScrapError(Exception):
    pass


class ScrapThrottleError(ScrapError):
    pass


class ScrapNotFoundError(ScrapError):
    pass


class ScrapValidationError(ScrapError):
    pass




class BaseScrapper:

    REQUEST_TIME: Histogram | None = None
    REQUEST_ERRORS: Counter | None = None

    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.logger = getLogger()

    async def url(self, sub: ScrapSource) -> str:
        return sub.to_url(json=True)

    def headers(self) -> dict | None:
        return None

    async def get_posts(self, sub: ScrapSource) -> List[Post]:
        t = time.time()
        u = await self.url(sub)
        try:
            self.logger.debug(f"Will fetch: {u}")
            async with self.session.get(u, headers=self.headers()) as req:
                self.logger.debug("Got reply for %s: %s %s %s",
                                  sub.to_str_tuple(), req.status, req.content_type, req.content_length)
                data = await req.text()

                if not req.ok:
                    insta_throttle = (req.status == 401 and "wait a few minutes" in data)
                    if req.status == 429 or insta_throttle:
                        self.logger.debug(f"payload: {data}, headers: {req.headers}")
                        if insta_throttle:
                            s = random.randint(60, 20 * 60)
                            self.logger.debug("Replacing session, sleeping for %s seconds", s)
                            await self.session.close()
                            await asyncio.sleep(s)
                            self.session = aiohttp.ClientSession(headers={"User-Agent": UserAgent().random})
                        self.REQUEST_ERRORS.labels(error_type="throttle_error", sub_name=sub.params.to_str_tuple()).inc()
                        raise ScrapThrottleError("Too many requests")
                    elif req.status == 404:
                        self.REQUEST_ERRORS.labels(error_type="not_found", sub_name=sub.params.to_str_tuple()).inc()
                        raise ScrapNotFoundError("Listing not found")
                    else:
                        self.REQUEST_ERRORS.labels(error_type=f"http_error_{req.status}", sub_name=sub.params.to_str_tuple()).inc()
                        raise ScrapError(f"Got error {req.status} from {u}, {data}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            self.REQUEST_ERRORS.labels(error_type=f"client_error_{ex.__class__.__name__}", sub_name=sub.params.to_str_tuple()).inc()
            raise ScrapError(f"Client error {str(ex)}") from ex
        finally:
            self.REQUEST_TIME.observe(time.time() - t)
        return self.data_to_posts(sub, data)

    def data_to_posts(self, sub: ScrapSource, data: str) -> List[Post]:
        pass

    @staticmethod
    def fix_url(url: str) -> str:
        return url.replace("&amp;", "&")

    @property
    def max_pause(self):
        return 600

    @property
    def default_pause(self):
        return 10
