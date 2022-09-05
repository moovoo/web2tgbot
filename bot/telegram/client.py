import asyncio
from logging import getLogger
from typing import List

import aiohttp
from pydantic import parse_raw_as

from bot.common.settings import get_settings
from bot.telegram.telegram_models import TelegramSendPhotoRequest, TelegramSendVideoRequest, TelegramSendMessageRequest, \
    TelegramSendMediaGroupRequest, TelegramCopyMessageRequest, TelegramRequest, TelegramReply, InputMedia, Message, \
    MessageId


class TelegramClientException(Exception):
    pass


class TelegramClientBadRequest(TelegramClientException):
    pass


class TelegramClientSizeException(TelegramClientBadRequest):
    pass


class TelegramClient:
    def __init__(self, token: str):
        self.token = token
        self.session = aiohttp.ClientSession()
        self.logger = getLogger()

    async def _send_request(self, request_method: str, request: TelegramSendPhotoRequest | TelegramSendVideoRequest | TelegramSendMessageRequest | TelegramSendMediaGroupRequest | TelegramCopyMessageRequest):
        data: aiohttp.FormData | None = None
        json: TelegramRequest | None = None

        if (type(request) is TelegramSendVideoRequest and type(request.video) is bytes) or \
           (type(request) is TelegramSendPhotoRequest and type(request.photo) is bytes):
            data = aiohttp.FormData()
            data.add_field("chat_id", str(request.chat_id))
            if request.caption:
                data.add_field("caption", request.caption)
            if request.parse_mode:
                data.add_field("parse_mode", request.parse_mode)

            if type(request) is TelegramSendVideoRequest and request.video:
                data.add_field("video", request.video)
            if type(request) is TelegramSendPhotoRequest and request.photo:
                data.add_field("photo", request.photo)

        else:
            json = request

        while True:
            try:
                self.logger.debug("Going to %s", request_method)
                async with self.session.post(get_settings().BOT_URL + self.token + "/" + request_method,
                                             data=data, json=json.dict() if json else None) as req:
                    self.logger.debug("Got %s %s %s", req.status, req.content_type, req.content_length)
                    if not req.ok:
                        text = await req.text()
                        if req.status == 413:
                            self.logger.error("Request too big!")
                            raise TelegramClientSizeException()
                        elif req.status == 400:
                            self.logger.error("Bad request")
                            raise TelegramClientBadRequest(f"Bad request {req.status} {text}")
                        else:
                            raise TelegramClientException(f"Unexpected status {req.status} {text}")

                    reply: TelegramReply = parse_raw_as(TelegramReply, await req.text())
                    if not reply.ok:

                        raise TelegramClientException(f"Reply was not ok: {reply.error_code}, {reply.description}")
                    return reply.result

            except aiohttp.ClientError:
                self.logger.exception("Got unexpected client error")

            await asyncio.sleep(1)

    async def send_message(self, chat_id: str | int, text: str, parse_mode: str = "HTML") -> Message:
        req = TelegramSendMessageRequest(chat_id=chat_id,
                                         text=text,
                                         parse_mode=parse_mode)

        return await self._send_request("sendMessage", req)

    async def send_photo(self, chat_id: str | int, *, caption: str | None = None, parse_mode: str | None = "HTML",
                         photo_url: str | None = None, photo_bytes: bytes | None = None):
        req = TelegramSendPhotoRequest(chat_id=chat_id,
                                       photo=photo_url or photo_bytes,
                                       caption=caption,
                                       parse_mode=parse_mode)
        return await self._send_request("sendPhoto", req)

    async def send_video(self, chat_id: str | int, *, caption: str | None = None, parse_mode: str | None = "HTML",
                         video_url: str | None = None, video_bytes: bytes | None = None):
        req = TelegramSendVideoRequest(chat_id=chat_id,
                                       video=video_url or video_bytes,
                                       caption=caption,
                                       parse_mode=parse_mode)
        return await self._send_request("sendVideo", req)

    async def copy_message(self, chat_id: str | int, from_chat_id: str | int, message_id: int) -> MessageId:
        req = TelegramCopyMessageRequest(chat_id=chat_id,
                                         from_chat_id=from_chat_id,
                                         message_id=message_id)
        return await self._send_request("copyMessage", req)

    async def send_media_group(self, chat_id: str | int, media: List[InputMedia]) -> List[Message]:
        req = TelegramSendMediaGroupRequest(chat_id=chat_id,
                                            media=media)
        return await self._send_request("sendMediaGroup", req)
