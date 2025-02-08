from typing import List

from pydantic import BaseModel


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
    source_id: str
    source_text: str | None = None
    original_url: str | None = None
    text: str
    url: str
    images: List[MediaItem] | None = None
    videos: List[MediaItem] | None = None


class OutboundMessage(BaseModel):
    conversation_ids: List[str]
    post: Post | None = None
    text: str | None = None
