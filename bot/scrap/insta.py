import json
from typing import List

import re
from urllib.parse import quote

import aiohttp
import pydantic
from prometheus_client import Counter, Histogram

from bot.common.cache import get_new_cache, Cache
from bot.common.configuration import get_configuration
from bot.common.models import ScrapSource, Post, MediaItem
from bot.common.settings import get_settings
from bot.scrap.insta_models import InstaReply, MediaNode
from bot.scrap.basescrapper import BaseScrapper, ScrapValidationError, ScrapError

class InstaUnknownUserid(Exception):
    pass

class InstaPosts(BaseScrapper):
    REQUEST_TIME = Histogram(name="instagram_client_request_time", documentation="Time spent waiting for reddit client request")
    REQUEST_ERRORS = Counter(name="instagram_client_errors", documentation="Reddit client errors",
                                labelnames=["error_type", "sub_name"])

    def __init__(self, cache: Cache):
        super().__init__()
        self.cache = cache

    # async def url(self, scrap_source: ScrapSource) -> str:
    #     base_url = scrap_source.to_url(json=True)
    #     variables = {
    #         "id": await self.get_instagram_user_id(scrap_source.params.username),
    #         "first": 10,
    #         "after": None,
    #     }
    #     return base_url + quote(json.dumps(variables))

    async def get_instagram_user_id(self, username: str) -> str:
        key = f"instagram_{username}"

        uid = await self.cache.get_item(key)
        if uid:
            return uid
        async with aiohttp.ClientSession() as session:
            self.logger.info(f"Getting instagram user id for {username}")
            async with session.get(f"https://www.instagram.com/{username}/") as response:
                text = await response.text()
                found = re.search(r'user_id\":\s?\"(\d+)\"', text)
                if found:
                    uid = found.group(1)
                    await self.cache.store_item(key, uid)
                    self.logger.info(f"Instagram user id for {username} saved as {uid}")
                    return uid
                else:
                    self.REQUEST_ERRORS.labels(error_type="instagram_user_id_missing", sub_name=username)
                    self.logger.warning(f"Instagram user id for {username} not found")
                    raise InstaUnknownUserid()

    def headers(self):
        return {"x-ig-app-id": "936619743392459"}

    def data_to_posts(self, sub: ScrapSource, data: str) -> List[Post]:
        try:
            reply = InstaReply.model_validate_json(data)
        except pydantic.ValidationError as ex:
            self.REQUEST_ERRORS.labels(error_type=f"validation_error", sub_name=sub.params.to_str_tuple()).inc()
            self.logger.error(data)
            self.logger.error(ex.errors())
            raise ScrapValidationError()

        if reply.status != "ok":
            raise ScrapError("Reply is not ok")

        user_id = reply.data.user.username
        return [self.insta_item_to_post(sub.to_str_tuple(), user_id, item.node) for item in reply.data.user.edge_owner_to_timeline_media.edges]


    def parse_dash_xml(self, xml: str) -> MediaItem | None:
        if not xml:
            return None

        items = re.findall('(?P<mime_type>video/mp4|AudioChannelConfiguration)[^<]+<BaseURL>(?P<url>[^>]+)</BaseURL>', xml)

        if items:
            urls = []
            audio = None
            for mime_type, url in items:
                if mime_type == 'video/mp4':
                    urls.append(self.fix_url(url))
                elif mime_type == 'AudioChannelConfiguration':
                    audio = self.fix_url(url)

            return MediaItem(urls=urls, audio=audio)


    def insta_item_to_post(self, source_id: str, insta_user_id: str, media_node: MediaNode) -> Post:

        text = "_"
        try:
            text = media_node.edge_media_to_caption.edges[0].node.text
        except (AttributeError, IndexError):
            pass

        images = None
        videos = None

        url = ""
        if media_node.typename in ("GraphImage", "GraphSidecar"):
            url = f"https://www.instagram.com/{insta_user_id}/p/{media_node.shortcode}"
            if media_node.typename == "GraphImage":
                images = [MediaItem(urls=[media_node.display_url])]
            if media_node.typename == "GraphSidecar":
                images = [
                    MediaItem(urls=[item.node.display_url]) for item in media_node.edge_sidecar_to_children.edges
                ]
        elif media_node.typename == "GraphVideo":
            url = f"https://www.instagram.com/{insta_user_id}/reel/{media_node.shortcode}"
            if media_node.dash_info.video_dash_manifest:
                if parsed := self.parse_dash_xml(media_node.dash_info.video_dash_manifest):
                    videos = [parsed]
            elif media_node.video_url:
                videos = [MediaItem(urls=[media_node.video_url])]
        return Post(
            unique_id=media_node.shortcode,
            source_id=source_id,
            source_text=insta_user_id,
            original_url=f"https://www.instagram.com/{insta_user_id}/",
            text="",
            text_block=text,
            url=url,
            images=images if images else None,
            videos=videos if videos else None,
        )

    @property
    def max_pause(self):
        return 120*60

    @property
    def default_pause(self):
        return 60*60
