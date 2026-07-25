import asyncio
import hashlib
import random
import time
from logging import getLogger
from pathlib import Path
from typing import List, Counter, Any
from urllib.parse import urlparse

from prometheus_client import Histogram

try:
    from cloakbrowser import launch_async, launch_context_async
    CLOAK = True
except ImportError:
    CLOAK = False
from playwright.async_api import async_playwright
from playwright.async_api import Playwright, Browser, BrowserContext, Page, APIResponse, Error

from bot.common.models import ScrapSource, Post
from bot.common.settings import get_settings


class HttpProviderError(Exception):
    pass


class BaseHttpProvider:

    def __init__(self, headless=True):
        self.logger = getLogger(__name__)
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        # self._cw: Any = None
        self.headless = headless

    async def _cleanup(self):
        if self.page:
            try:
                await self.page.close()
            except Exception as e:
                self.logger.warning(f"Error closing page during cleanup: {e}")
            self.page = None
        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                self.logger.warning(f"Error closing context during cleanup: {e}")
            self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                self.logger.warning(f"Error closing browser during cleanup: {e}")
            self.browser = None
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping playwright during cleanup: {e}")
            self.playwright = None

    async def start(self):
        if Path("state.json").exists():
            storage = "state.json"
        else:
            storage = None
        if CLOAK:
            self.context = await launch_context_async(headless=self.headless,
                                                      storage_state=storage,
                                                      )
            # self.context = self._cw.context
            self.page = await self.context.new_page()
            self.logger.info("Started with cloakbrowser")
        else:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless, )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            self.logger.info("Started with playwright")

    async def stop(self):
        await self._cleanup()
        self.logger.info("Stopped http provider")

    async def reset(self):
        self.logger.warning("Resetting http provider due to timeout")
        await self._cleanup()
        await self.start()

    async def get(self, url: str, **kwargs) -> APIResponse:
        if not self.context:
            raise HttpProviderError("HttpProvider not started, call start() first")
        timeout = get_settings().http_timeout
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                await asyncio.wait_for(self.login(), timeout=timeout)
                response = await asyncio.wait_for(self.context.request.get(url, **kwargs), timeout=timeout)
                return response
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    self.logger.warning(f"Request to {url} timed out on attempt {attempt + 1}/{max_retries + 1}, resetting and retrying")
                    await self.reset()
                    continue
                self.logger.error(f"Request to {url} timed out after {max_retries + 1} attempts")
                raise

    async def login(self):
        await self.context.storage_state(path="state.json")

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
    FETCH_THROTTLE_INTERVAL = 1.0

    def __init__(self, provider: BaseHttpProvider):
        # self.session = aiohttp.ClientSession()
        self.logger = getLogger()
        self.http_provider = provider
        self._last_fetch_time = 0.0

    async def url(self, sub: ScrapSource) -> str:
        return sub.to_url(json=True)

    def headers(self) -> dict | None:
        return None

    async def start(self):
        await self.http_provider.start()

    async def stop(self):
        await self.http_provider.stop()

    async def fetch_data(self, url: str, sub: ScrapSource | None = None) -> bytes:
        now = time.time()
        elapsed = now - self._last_fetch_time
        if elapsed < self.FETCH_THROTTLE_INTERVAL:
            await asyncio.sleep(self.FETCH_THROTTLE_INTERVAL - elapsed)
        self.logger.debug(f"Will fetch: {url}")
        req = await self.http_provider.get(url)
        self._last_fetch_time = time.time()
        if sub:
            self.logger.debug("Got reply for %s: %s %s %s",
                              sub.to_str_tuple(), req.status, req.headers.get("Content-Type"), req.headers.get("Content-Length"))
        data = await req.body()

        if not req.ok:
            data_str = data.decode('utf-8', errors='replace')
            if sub:
                insta_throttle = (req.status == 401 and "wait a few minutes" in data_str)
                if req.status == 429 or insta_throttle:
                    self.logger.debug(f"payload: {data_str}, headers: {req.headers}")
                    raise ScrapThrottleError("Too many requests")
                elif req.status == 404:
                    self.REQUEST_ERRORS.labels(error_type="not_found", sub_name=sub.params.to_str_tuple()).inc()
                    raise ScrapNotFoundError("Listing not found")
                else:
                    self.REQUEST_ERRORS.labels(error_type=f"http_error_{req.status}", sub_name=sub.params.to_str_tuple()).inc()
                    raise ScrapError(f"Got error {req.status} from {url}, {data_str}")
            else:
                if req.status == 429:
                    raise ScrapThrottleError("Too many requests")
                elif req.status == 404:
                    raise ScrapNotFoundError("Resource not found")
                else:
                    raise ScrapError(f"Got error {req.status} from {url}, {data_str}")
        return data

    async def get_posts(self, sub: ScrapSource) -> List[Post]:
        t = time.time()
        u = await self.url(sub)
        try:
            data = (await self.fetch_data(u, sub)).decode('utf-8')
        except (Error, asyncio.TimeoutError) as ex:
            self.REQUEST_ERRORS.labels(error_type=f"client_error_{ex.__class__.__name__}", sub_name=sub.params.to_str_tuple()).inc()
            raise ScrapError(f"Client error {str(ex)}") from ex
        finally:
            self.REQUEST_TIME.observe(time.time() - t)
        posts = self.data_to_posts(sub, data)
        self.logger.debug(f"Found some posts: {len(posts)}")
        return posts

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

    async def _download_url(self, url: str, post: Post, download_dir: Path) -> str | None:
        try:
            body = await self.fetch_data(url)
            parsed_url = Path(urlparse(url).path)
            file_hash = hashlib.sha256(body).hexdigest()[:12]
            stem = parsed_url.stem or file_hash
            suffix = parsed_url.suffix or ""
            filename = f"{post.unique_id}_{stem}_{file_hash}{suffix}"
            filepath = download_dir / filename
            filepath.write_bytes(body)
            self.logger.debug("Downloaded %s -> %s", url, filepath)
            return str(filepath)
        except Exception as e:
            self.logger.error("Failed to download %s: %s", url, e)
            return None

    async def download_media(self, posts: List[Post], path: str) -> List[Post]:
        download_dir = Path(path).resolve()
        download_dir.mkdir(parents=True, exist_ok=True)

        for post in posts:
            for media_list in (post.images or [], post.videos or []):
                for media_item in media_list:
                    downloaded = None
                    urls = reversed(media_item.urls) if media_list is post.videos else media_item.urls
                    for url in urls:
                        downloaded = await self._download_url(url, post, download_dir)
                        if downloaded:
                            break
                    if downloaded:
                        media_item.urls = [downloaded]
                    else:
                        self.logger.warning("All URLs failed for media item in post %s", post.unique_id)

            if post.videos:
                for media_item in post.videos:
                    if media_item.audio:
                        downloaded = await self._download_url(media_item.audio, post, download_dir)
                        if downloaded:
                            media_item.audio = downloaded

        return posts
