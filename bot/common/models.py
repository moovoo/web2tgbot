from enum import StrEnum
from typing import List
from urllib.parse import urlparse, parse_qs

from pydantic import BaseModel

from bot.common.settings import get_settings


class IncomingMessage(BaseModel):
    conversation_id: str
    from_user_id: str
    payload: str
    provider: str
    message_id: str | None = None


class MediaItem(BaseModel):
    urls: List[str]
    caption: str | None = None
    audio: str | None = None


class Post(BaseModel):
    unique_id: str
    source_id: str
    source_text: str | None = None
    original_url: str | None = None
    text: str
    url: str
    text_block: str | None = None
    images: List[MediaItem] | None = None
    videos: List[MediaItem] | None = None


class OutboundMessage(BaseModel):
    conversation_ids: List[str]
    post: Post | None = None
    text: str | None = None


DELIM = "#"

class BadSourceException(Exception):
    pass

class ScrapSourceType(StrEnum):
    Reddit = "reddit"
    Instagram = "instagram"

class RedditScrapParams(BaseModel):
    subreddit: str
    sorting: str
    timing: str | None = None

    def to_str_tuple(self):
        return f"{self.subreddit}{DELIM}{self.sorting}{DELIM}{self.timing}"

    def to_path(self, json=False) -> str:
        path = f"{self.subreddit}/{self.sorting}/"
        if json:
            path += ".json"
        if self.timing:
            path += f"?t={self.timing}"
        return path

    @staticmethod
    def from_path(path, query) -> 'RedditScrapParams':
        try:
            _, r, subreddit, sorting, *__ = path.split("/")
        except ValueError:
            raise BadSourceException("Bad reddit path")
        if r != "r":
            raise BadSourceException("Not a subreddit path")

        timing = None

        parsed_query = parse_qs(query)
        try:
            timing = parsed_query['t'][0]
        except (KeyError, IndexError):
            pass

        return RedditScrapParams(subreddit=subreddit, sorting=sorting or "hot", timing=timing)

    @staticmethod
    def from_str_tuple(str_tuple: str) -> 'RedditScrapParams':
        subreddit, sorting, timing = str_tuple.split(DELIM)
        return RedditScrapParams(subreddit=subreddit, sorting=sorting, timing=timing)

class InstagramScrapParams(BaseModel):
    username: str

    def to_str_tuple(self):
        return self.username

    def to_path(self, json=False) -> str:
        if json:
            # return "graphql/query/?query_id=9957820854288654&variables="
            # return "graphql/query/?query_id=17888483320059182&variables="
            return f"api/v1/users/web_profile_info/?username={self.username}"
        else:
            return f"{self.username}/"

    @staticmethod
    def from_path(path, query) -> 'InstagramScrapParams':
        try:
            _, username, *__ = path.split("/")
        except ValueError:
            raise BadSourceException("Bad instagram path")
        if not username:
            raise BadSourceException("Bad instagram user path")
        return InstagramScrapParams(username=username)

    @staticmethod
    def from_str_tuple(str_tuple: str):
        return InstagramScrapParams(username=str_tuple)

class ScrapSource(BaseModel):
    source_type: ScrapSourceType
    params: RedditScrapParams | InstagramScrapParams

    def to_str_tuple(self) -> str:
        return f"{self.source_type.value}@{self.params.to_str_tuple()}"

    @staticmethod
    def from_str_tuple(source_str: str) -> 'ScrapSource':
        t, args = source_str.split("@")
        match t:
            case ScrapSourceType.Reddit.value:
                return ScrapSource(source_type=ScrapSourceType(t), params=RedditScrapParams.from_str_tuple(args))
            case ScrapSourceType.Instagram.value:
                return ScrapSource(source_type=ScrapSourceType(t), params=InstagramScrapParams.from_str_tuple(args))
            case _:
                raise BadSourceException(f"Unknown scrap source: {source_str}")

    @staticmethod
    def from_url(url: str) -> 'ScrapSource':
        result = urlparse(url)

        match result.hostname:
            case "instagram.com"|"www.instagram.com":
                return ScrapSource(source_type=ScrapSourceType.Instagram,
                                   params=InstagramScrapParams.from_path(result.path, result.query))
            case "reddit.com"|"www.reddit.com"|"new.reddit.com"|"old.reddit.com":
                return ScrapSource(source_type=ScrapSourceType.Reddit,
                                   params=RedditScrapParams.from_path(result.path, result.query))
            case _:
                raise BadSourceException(f"Unknown scrap source {url}")


    def to_url(self, json=False) -> str:
        match self.source_type.value:
            case ScrapSourceType.Reddit.value:
                return f"{get_settings().RD_BASE_URL}{self.params.to_path(json=json)}"
            case ScrapSourceType.Instagram.value:
                return f"{get_settings().INSTA_BASE_URL}{self.params.to_path(json=json)}"
        raise BadSourceException(f"Unknown source type: {self.source_type.value}")