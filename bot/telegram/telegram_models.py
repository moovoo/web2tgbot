from __future__ import annotations
from typing import Any, List
from pydantic import BaseModel, Field


class TelegramException(Exception):
    pass


class InputMedia(BaseModel):
    type: str
    media: str
    caption: str | None
    parse_mode: str | None


class MessageId(BaseModel):
    message_id: int


class TelegramRequest(BaseModel):
    chat_id: str | int


class TelegramSendMessageRequest(TelegramRequest):
    text: str
    parse_mode: str | None


class TelegramCopyMessageRequest(TelegramRequest):
    from_chat_id: str | int
    message_id: int


class TelegramSendPhotoRequest(TelegramRequest):
    photo: str | bytes
    caption: str | None
    parse_mode: str | None


class TelegramSendVideoRequest(TelegramRequest):
    video: str | bytes
    caption: str | None
    parse_mode: str | None


class TelegramSendMediaGroupRequest(TelegramRequest):
    media: List[InputMedia]


class GetUpdates(BaseModel):
    offset: int | None
    limit: int | None
    timeout: int | None
    allowed_updates: List[str] | None


class ResponseParameters(BaseModel):
    migrate_to_chat_id: int | None
    retry_after: int | None


class TelegramReply(BaseModel):
    ok: bool
    result: List[Update] | MessageId | Message | List[Message] | None
    description: str | None
    error_code: int | None
    parameters: ResponseParameters | None


class User(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool | None
    added_to_attachment_menu: bool | None
    can_join_groups: bool | None
    can_read_all_group_messages: bool | None
    supports_inline_queries: bool | None


class MessageEntity(BaseModel):
    type: str
    offset: int
    length: int
    url: str | None
    user: User | None
    language: str | None


class Message(MessageId):
    from_user: User | None = Field(alias="from")
    sender_chat: Chat | None
    date: int
    chat: Chat
    forward_from: User | None
    forward_from_chat: Chat | None
    forward_from_message_id: int | None
    forward_signature: str | None
    forward_sender_name: str | None
    forward_date: int | None
    is_automatic_forward: bool | None
    reply_to_message: Message | None
    via_bot: User | None
    edit_date: int | None
    has_protected_content: bool | None
    media_group_id: str | None
    author_signature: str | None
    text: str | None
    entities: List[MessageEntity] | None
    animation: Any | None  # todo: Animation
    audio: Any | None  # todo: Audio
    document: Any | None  # todo: Document
    photo: List[Any] | None  # todo: PhotoSize
    sticker: Any | None  # todo: Sticker
    video: Any | None  # todo: Video
    video_note: Any | None  # todo: VideoNote
    voice: Any | None  # todo: Voice
    caption: str | None
    caption_entities: List[MessageEntity] | None
    contact: Any | None  # todo: Contact
    dice: Any | None  # todo: Dice
    game: Any | None  # todo: Game
    poll: Any | None  # todo: Poll
    venue: Any | None  # todo: Venue
    location: Any | None  # todo: Location
    new_chat_members: List[User] | None
    left_chat_member: User | None
    new_chat_title: str | None
    new_chat_photo: List[Any] | None  # todo: PhotoSize
    delete_chat_photo: bool | None
    group_chat_created: bool | None
    supergroup_chat_created: bool | None
    channel_chat_created: bool | None
    message_auto_delete_timer_changed: Any | None  # todo: MessageAutoDeleteTimerChanged
    migrate_to_chat_id: int | None
    migrate_from_chat_id: int | None
    pinned_message: Message | None
    invoice: Any | None  # todo: Invoice
    successful_payment: Any | None  # todo: SuccessfulPayment
    connected_website: str | None
    passport_data: Any | None  # todo: PassportData
    proximity_alert_triggered: Any | None  # todo: ProximityAlertTriggered
    video_chat_scheduled: Any | None  # todo: VideoChatScheduled
    video_chat_started: Any | None  # todo: VideoChatStarted
    video_chat_ended: Any | None  # todo: VideoChatEnded
    video_chat_participants_invited: Any | None  # todo: VideoChatParticipantsInvited
    web_app_data: Any | None  # todo: WebAppData
    reply_markup: Any | None  # todo: InlineKeyboardMarkup


class Chat(BaseModel):
    id: int
    type: str
    title: str | None
    username: str | None
    first_name: str | None
    last_name: str | None
    photo: Any | None  # todo: ChatPhoto
    bio: str | None
    has_private_forwards: bool | None
    join_to_send_messages: bool | None
    join_by_request: bool | None
    description: str | None
    invite_link: str | None
    pinned_message: Message | None
    permissions: Any | None  # todo: ChatPermissions
    slow_mode_delay: int | None
    message_auto_delete_time: int | None
    has_protected_content: bool | None
    sticker_set_name: str | None
    can_set_sticker_set: bool | None
    linked_chat_id: int | None
    location: Any | None  # todo: ChatLocation


class Update(BaseModel):
    update_id: int
    message: Message | None
    edited_message: Message | None
    channel_post: Message | None
    edited_channel_post: Message | None
    inline_query: Any | None  # todo: InlineQuery
    chosen_inline_result: Any | None  # todo: ChosenInlineResult
    callback_query: Any | None  # todo: CallbackQuery
    shipping_query: Any | None  # todo: ShippingQuery
    pre_checkout_query: Any | None  # todo: PreCheckoutQuery
    poll: Any | None  # todo: Poll
    poll_answer: Any | None  # todo: PollAnswer
    my_chat_member: Any | None  # todo: ChatMemberUpdated
    chat_member: Any | None  # todo: ChatMemberUpdated
    chat_join_request: Any | None  # todo: ChatJoinRequest


Message.update_forward_refs()
Chat.update_forward_refs()
TelegramReply.update_forward_refs()
