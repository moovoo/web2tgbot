from __future__ import annotations

from typing import List, Dict
from urllib.parse import urlparse, parse_qs

from pydantic import BaseModel, Field


class BadRedditUrlException(Exception):
    pass


DELIM = "#"


class SubredditListing(BaseModel):
    subreddit: str
    sorting: str
    timing: str | None

    def to_str_tuple(self):
        return f"{self.subreddit}{DELIM}{self.sorting}{DELIM}{self.timing if self.timing else ''}"

    @staticmethod
    def from_str_tuple(source_str: str):
        subreddit, sorting, timing = source_str.split(DELIM)
        return SubredditListing(subreddit=subreddit, sorting=sorting, timing=timing)

    @staticmethod
    def from_url(url: str):
        result = urlparse(url)
        if result.hostname not in ("reddit.com", "www.reddit.com"):
            raise BadRedditUrlException("Bad hostname: " + str(result.hostname))

        try:
            _, r, subreddit, sorting, *__ = result.path.split("/")
        except ValueError:
            raise BadRedditUrlException("Can't unpack path: " + result.path)
        if r != "r":
            raise BadRedditUrlException("Not a subreddit path: " + result.path)

        timing = None

        parsed_query = parse_qs(result.query)
        try:
            timing = parsed_query['t'][0]
        except (KeyError, IndexError):
            pass

        return SubredditListing(subreddit=subreddit, sorting=sorting or "hot", timing=timing)

    def to_url(self, json: bool = False) -> str:
        url = f"https://www.reddit.com/r/{self.subreddit}/{self.sorting}/"
        if json:
            url += ".json"
        if self.timing:
            url += f"?t={self.timing}"
        return url


class ImageMetadata(BaseModel):
    x: int
    y: int
    u: str


class MediaMetadata(BaseModel):
    status: str
    e: str
    m: str
    o: List[ImageMetadata] | None
    p: List[ImageMetadata] | None
    s: ImageMetadata | None


class PreviewImageItem(BaseModel):
    url: str
    width: int
    height: int


class PreviewImageVariantsOptions(BaseModel):
    source: PreviewImageItem | None
    resolutions: List[PreviewImageItem] | None


class PreviewImageVariants(BaseModel):
    gif: PreviewImageVariantsOptions | None
    mp4: PreviewImageVariantsOptions | None
    obfuscated: PreviewImageVariantsOptions | None
    nsfw: PreviewImageVariantsOptions | None


class PreviewImage(BaseModel):
    id: str
    source: PreviewImageItem | None
    resolutions: List[PreviewImageItem] | None
    variants: PreviewImageVariants | None


class RedditVideoPreview(BaseModel):
    bitrate_kbps: int
    fallback_url: str
    width: int
    height: int
    scrubber_media_url: str
    duration: int
    dash_url: str
    hls_url: str
    is_gif: bool
    transcoding_status: str


class Preview(BaseModel):
    images: List[PreviewImage] | None
    reddit_video_preview: RedditVideoPreview | None
    enabled: bool


class Embed(BaseModel):
    provider_url: str | None
    title: str | None
    html: str | None
    thumbnail_url: str | None
    type_: str | None = Field(alias="type")


class Media(BaseModel):
    reddit_video: RedditVideoPreview | None
    oembed: Embed | None
    type_: str | None = Field(alias="type")


class GalleryItem(BaseModel):
    caption: str | None
    media_id: str
    id: int


class GalleryData(BaseModel):
    items: List[GalleryItem]


class RedditPost(BaseModel):
    subreddit: str
    title: str | None
    name: str
    thumbnail: str | None
    created: int
    created_utc: int
    subreddit_id: str
    id: str
    author: str
    permalink: str
    url: str | None
    is_video: bool
    preview: Preview | None
    media: Media | None
    secure_media: Media | None
    media_metadata: Dict[str, MediaMetadata] | None
    crosspost_parent_list: List[RedditPost] | None
    gallery_data: GalleryData | None
    subreddit_name_prefixed: str | None


class Item(BaseModel):
    kind: str
    data: RedditPost


class Listing(BaseModel):
    after: str | None
    dist: int
    modhash: str | None
    geo_filter: str | None
    children: List[Item] | None
    before: str | None


class RedditReply(BaseModel):
    kind: str
    data: Listing


RedditPost.update_forward_refs()
