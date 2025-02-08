import asyncio
from logging import getLogger
from typing import List

import aiohttp

from bot.common.settings import get_settings
from bot.telegram.telegram_models import TelegramSendPhotoRequest, TelegramSendVideoRequest, TelegramSendMessageRequest, \
    TelegramSendMediaGroupRequest, TelegramCopyMessageRequest, TelegramRequest, TelegramReply, InputMedia, Message, \
    MessageId, Chat

from prometheus_client import Histogram, Counter
from prometheus_async.aio import time

class TelegramClientException(Exception):
    pass


class TelegramClientBadRequest(TelegramClientException):
    pass


class TelegramClientForbidden(TelegramClientException):
    pass


class TelegramClientSizeException(TelegramClientBadRequest):
    pass


class TelegramClient:

    TG_REQUEST_TIME = Histogram(name="tg_client_request_time", documentation="Time spent waiting for TG client request")
    TG_REQUEST_ERRORS = Counter(name="tg_client_errors", documentation="Client errors",
                                labelnames=["error_type"])

    def __init__(self, token: str):
        self.token = token
        self.session = aiohttp.ClientSession()
        self.logger = getLogger()

    @time(TG_REQUEST_TIME)
    async def _send_request(self, request_method: str, request: TelegramRequest | TelegramSendPhotoRequest | TelegramSendVideoRequest | TelegramSendMessageRequest | TelegramSendMediaGroupRequest | TelegramCopyMessageRequest):
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
                                             data=data, json=json.model_dump() if json else None) as req:
                    self.logger.debug("Got %s %s %s", req.status, req.content_type, req.content_length)
                    if not req.ok:
                        text = await req.text()
                        if req.status == 413:
                            self.logger.error("Request too big!")
                            self.TG_REQUEST_ERRORS.labels("too_big").inc()
                            raise TelegramClientSizeException()
                        elif req.status == 400:
                            self.logger.error("Bad request")
                            self.TG_REQUEST_ERRORS.labels("bad_request").inc()
                            raise TelegramClientBadRequest(f"Bad request {req.status} {text}")
                        elif req.status == 403:
                            self.logger.error("Forbidden")
                            self.TG_REQUEST_ERRORS.labels("forbidden").inc()
                            raise TelegramClientForbidden(f"Forbidden {req.status} {text}")
                        else:
                            self.TG_REQUEST_ERRORS.labels(f"http_{req.status}").inc()
                            raise TelegramClientException(f"Unexpected status {req.status} {text}")

                    reply: TelegramReply = TelegramReply.model_validate_json(await req.text())
                    if not reply.ok:
                        self.TG_REQUEST_ERRORS.labels(f"server_error_{reply.error_code}").inc()
                        raise TelegramClientException(f"Reply was not ok: {reply.error_code}, {reply.description}")
                    return reply.result

            except aiohttp.ClientError as ex:
                self.TG_REQUEST_ERRORS.labels(f"http_client_error_{ex.__class__.__name__.lower()}").inc()
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

    async def get_chat(self, chat_id: str | int) -> Chat:
        req = TelegramRequest(chat_id=chat_id)
        return await self._send_request("getChat", req)
