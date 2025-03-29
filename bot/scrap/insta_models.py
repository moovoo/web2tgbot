from typing import List

from pydantic import BaseModel, Field


class PageInfo(BaseModel):
    has_next_page: bool
    end_cursor: str

class CaptionNodeText(BaseModel):
    text: str

class CaptionNode(BaseModel):
    node: CaptionNodeText

class CaptionEdge(BaseModel):
    edges: List[CaptionNode]

class ThumbnailResources(BaseModel):
    src: str
    config_width: int
    config_height: int

class DashInfo(BaseModel):
    is_dash_eligible: bool | None = None
    video_dash_manifest: str | None = None
    number_of_qualities: int | None = None

class SidecarNodeBody(BaseModel):
    typename: str = Field(alias="__typename")
    id: str
    shortcode: str | None = None
    display_url: str
    is_video: bool
    dash_info: DashInfo | None = None

class SidecarNode(BaseModel):
    node: SidecarNodeBody

class SidecarEdge(BaseModel):
    edges: List[SidecarNode]

class Owner(BaseModel):
    id: str
    username: str

class MediaNode(BaseModel):
    typename: str = Field(alias="__typename")
    shortcode: str | None = None
    edge_media_to_caption: CaptionEdge
    thumbnail_resources: List[ThumbnailResources]
    dash_info: DashInfo | None = None
    video_url: str | None = None
    taken_at_timestamp: int
    edge_sidecar_to_children: SidecarEdge | None = None
    owner: Owner
    display_url: str

class MediaEdge(BaseModel):
    node: MediaNode

class TimeLineMedia(BaseModel):
    count: int
    page_info: PageInfo
    edges: List[MediaEdge]

class InstaUser(BaseModel):
    id: str | None = None
    username: str | None = None
    edge_owner_to_timeline_media: TimeLineMedia

class ReplyUser(BaseModel):
    user: InstaUser

class InstaReply(BaseModel):
    data: ReplyUser
    status: str