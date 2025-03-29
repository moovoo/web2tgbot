from __future__ import annotations

from typing import List, Dict

from pydantic import BaseModel, Field

class ImageMetadata(BaseModel):
    x: int
    y: int
    u: str | None = None
    gif: str | None = None
    mp4: str | None = None


class MediaMetadata(BaseModel):
    status: str | None = None
    e: str | None = None
    m: str | None = None
    o: List[ImageMetadata] | None = None
    p: List[ImageMetadata] | None = None
    s: ImageMetadata | None = None


class PreviewImageItem(BaseModel):
    url: str
    width: int
    height: int


class PreviewImageVariantsOptions(BaseModel):
    source: PreviewImageItem | None = None
    resolutions: List[PreviewImageItem] | None = None


class PreviewImageVariants(BaseModel):
    gif: PreviewImageVariantsOptions | None = None
    mp4: PreviewImageVariantsOptions | None = None
    obfuscated: PreviewImageVariantsOptions | None = None
    nsfw: PreviewImageVariantsOptions | None = None


class PreviewImage(BaseModel):
    id: str
    source: PreviewImageItem | None = None
    resolutions: List[PreviewImageItem] | None = None
    variants: PreviewImageVariants | None = None


class RedditVideoPreview(BaseModel):
    bitrate_kbps: int | None = None
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
    images: List[PreviewImage] | None = None
    reddit_video_preview: RedditVideoPreview | None = None
    enabled: bool


class Embed(BaseModel):
    provider_url: str | None = None
    title: str | None = None
    html: str | None = None
    thumbnail_url: str | None = None
    type_: str | None = Field(alias="type", default=None)


class Media(BaseModel):
    reddit_video: RedditVideoPreview | None = None
    oembed: Embed | None = None
    type_: str | None = Field(alias="type", default=None)


class GalleryItem(BaseModel):
    caption: str | None = None
    media_id: str
    id: int


class GalleryData(BaseModel):
    items: List[GalleryItem]


class RedditPost(BaseModel):
    subreddit: str
    title: str | None = None
    name: str
    thumbnail: str | None = None
    created: int
    created_utc: int
    subreddit_id: str
    id: str
    author: str
    permalink: str
    url: str | None = None
    is_video: bool
    preview: Preview | None = None
    media: Media | None = None
    secure_media: Media | None = None
    media_metadata: Dict[str, MediaMetadata] | None = None
    crosspost_parent_list: List[RedditPost] | None = None
    gallery_data: GalleryData | None = None
    subreddit_name_prefixed: str | None = None
    selftext: str | None = None
    selftext_html: str | None = None


class Item(BaseModel):
    kind: str
    data: RedditPost


class Listing(BaseModel):
    after: str | None = None
    dist: int
    modhash: str | None = None
    geo_filter: str | None = None
    children: List[Item] | None = None
    before: str | None = None


class RedditReply(BaseModel):
    kind: str
    data: Listing


RedditPost.model_rebuild()
