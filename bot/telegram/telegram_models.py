from __future__ import annotations
from typing import Any, List
from pydantic import BaseModel, Field


class TelegramException(Exception):
    pass


class InputMedia(BaseModel):
    type: str
    media: str
    caption: str | None = None
    parse_mode: str | None = None


class MessageId(BaseModel):
    message_id: int


class TelegramRequest(BaseModel):
    chat_id: str | int


class TelegramSendMessageRequest(TelegramRequest):
    text: str
    parse_mode: str | None = None


class TelegramCopyMessageRequest(TelegramRequest):
    from_chat_id: str | int
    message_id: int


class TelegramSendPhotoRequest(TelegramRequest):
    photo: str | bytes
    caption: str | None = None
    parse_mode: str | None = None


class TelegramSendVideoRequest(TelegramRequest):
    video: str | bytes
    caption: str | None = None
    parse_mode: str | None = None


class TelegramSendMediaGroupRequest(TelegramRequest):
    media: List[InputMedia]


class GetUpdates(BaseModel):
    offset: int | None = None
    limit: int | None = None
    timeout: int | None = None
    allowed_updates: List[str] | None = None


class ResponseParameters(BaseModel):
    migrate_to_chat_id: int | None = None
    retry_after: int | None = None


class TelegramReply(BaseModel):
    ok: bool
    result: List[Update] | MessageId | Message | List[Message] | Chat | None = None
    description: str | None = None
    error_code: int | None = None
    parameters: ResponseParameters | None = None


class User(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None
    added_to_attachment_menu: bool | None = None
    can_join_groups: bool | None = None
    can_read_all_group_messages: bool | None = None
    supports_inline_queries: bool | None = None


class MessageEntity(BaseModel):
    type: str
    offset: int
    length: int
    url: str | None = None
    user: User | None = None
    language: str | None = None


class Message(MessageId):
    from_user: User | None = Field(alias="from", default=None)
    sender_chat: Chat | None = None
    date: int
    chat: Chat
    forward_from: User | None = None
    forward_from_chat: Chat | None = None
    forward_from_message_id: int | None = None
    forward_signature: str | None = None
    forward_sender_name: str | None = None
    forward_date: int | None = None
    is_automatic_forward: bool | None = None
    reply_to_message: Message | None = None
    via_bot: User | None = None
    edit_date: int | None = None
    has_protected_content: bool | None = None
    media_group_id: str | None = None
    author_signature: str | None = None
    text: str | None = None
    entities: List[MessageEntity] | None = None
    animation: Any | None = None  # todo: Animation
    audio: Any | None = None  # todo: Audio
    document: Any | None = None  # todo: Document
    photo: List[Any] | None = None  # todo: PhotoSize
    sticker: Any | None = None  # todo: Sticker
    video: Any | None = None  # todo: Video
    video_note: Any | None = None  # todo: VideoNote
    voice: Any | None = None  # todo: Voice
    caption: str | None = None
    caption_entities: List[MessageEntity] | None = None
    contact: Any | None = None  # todo: Contact
    dice: Any | None = None  # todo: Dice
    game: Any | None = None  # todo: Game
    poll: Any | None = None  # todo: Poll
    venue: Any | None = None  # todo: Venue
    location: Any | None = None  # todo: Location
    new_chat_members: List[User] | None = None
    left_chat_member: User | None = None
    new_chat_title: str | None = None
    new_chat_photo: List[Any] | None = None  # todo: PhotoSize
    delete_chat_photo: bool | None = None
    group_chat_created: bool | None = None
    supergroup_chat_created: bool | None = None
    channel_chat_created: bool | None = None
    message_auto_delete_timer_changed: Any | None = None  # todo: MessageAutoDeleteTimerChanged
    migrate_to_chat_id: int | None = None
    migrate_from_chat_id: int | None = None
    pinned_message: Message | None = None
    invoice: Any | None = None  # todo: Invoice
    successful_payment: Any | None = None  # todo: SuccessfulPayment
    connected_website: str | None = None
    passport_data: Any | None = None  # todo: PassportData
    proximity_alert_triggered: Any | None = None  # todo: ProximityAlertTriggered
    video_chat_scheduled: Any | None = None  # todo: VideoChatScheduled
    video_chat_started: Any | None = None  # todo: VideoChatStarted
    video_chat_ended: Any | None = None  # todo: VideoChatEnded
    video_chat_participants_invited: Any | None = None  # todo: VideoChatParticipantsInvited
    web_app_data: Any | None = None  # todo: WebAppData
    reply_markup: Any | None = None  # todo: InlineKeyboardMarkup


class ChatPermissions(BaseModel):
    can_send_messages: bool | None = None
    can_send_media_messages: bool | None = None
    can_send_polls: bool | None = None
    can_send_other_messages: bool | None = None
    can_add_web_page_previews: bool | None = None
    can_change_info: bool | None = None
    can_invite_users: bool | None = None
    can_pin_messages: bool | None = None


class Chat(BaseModel):
    id: int
    type: str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo: Any | None = None  # todo: ChatPhoto
    bio: str | None = None
    has_private_forwards: bool | None = None
    join_to_send_messages: bool | None = None
    join_by_request: bool | None = None
    description: str | None = None
    invite_link: str | None = None
    pinned_message: Message | None = None
    permissions: ChatPermissions | None = None
    slow_mode_delay: int | None = None
    message_auto_delete_time: int | None = None
    has_protected_content: bool | None = None
    sticker_set_name: str | None = None
    can_set_sticker_set: bool | None = None
    linked_chat_id: int | None = None
    location: Any | None = None  # todo: ChatLocation


class Update(BaseModel):
    update_id: int
    message: Message | None = None
    edited_message: Message | None = None
    channel_post: Message | None = None
    edited_channel_post: Message | None = None
    inline_query: Any | None = None  # todo: InlineQuery
    chosen_inline_result: Any | None = None  # todo: ChosenInlineResult
    callback_query: Any | None = None  # todo: CallbackQuery
    shipping_query: Any | None = None  # todo: ShippingQuery
    pre_checkout_query: Any | None = None  # todo: PreCheckoutQuery
    poll: Any | None = None  # todo: Poll
    poll_answer: Any | None = None  # todo: PollAnswer
    my_chat_member: Any | None = None  # todo: ChatMemberUpdated
    chat_member: Any | None = None  # todo: ChatMemberUpdated
    chat_join_request: Any | None = None  # todo: ChatJoinRequest


Message.model_rebuild()
Chat.model_rebuild()
TelegramReply.model_rebuild()
