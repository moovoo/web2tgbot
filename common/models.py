from typing import List

from pydantic import BaseModel


class IncomingMessage(BaseModel):
    conversation_id: str
    from_user_id: str
    payload: str
    provider: str
    message_id: str | None


class MediaItem(BaseModel):
    urls: List[str]
    caption: str | None
    audio: str | None


class Post(BaseModel):
    source_id: str
    original_url: str | None
    text: str
    url: str
    images: List[MediaItem] | None
    videos: List[MediaItem] | None


class OutboundMessage(BaseModel):
    conversation_ids: List[str]
    post: Post | None
    text: str | None
