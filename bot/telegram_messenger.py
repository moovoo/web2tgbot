import asyncio
import logging.config
import os
import random
import signal
import tempfile
import uuid
from logging import getLogger
from typing import Tuple

import aiohttp
from pydantic import parse_raw_as

from bot.common.models import OutboundMessage, MediaItem
from bot.common.pubsub import get_new_pubsub
from bot.common.settings import get_settings
from bot.telegram.client import TelegramClient, TelegramClientBadRequest, TelegramClientForbidden
from bot.telegram.telegram_models import Message, InputMedia


class ProcessingError(Exception):
    pass


class TelegramMessenger:

    MAX_URL_SIZE = 20 * 1024 * 1000
    MAX_UPLOAD_SIZE = 50 * 1024 * 1000

    def __init__(self, token: str):
        self.logger = getLogger()
        self.token = token
        self.bot_id = token.split(":")[0]
        self.pubsub = get_new_pubsub()
        self.tg_client = TelegramClient(self.token)

    async def serve(self):
        reader = self.pubsub.stream_messages(f"telegram_{self.bot_id}")
        async for channel_id, message_id, message_raw in reader:

            outbound_message: OutboundMessage = parse_raw_as(OutboundMessage, message_raw)
            self.logger.debug("Got new message %s", outbound_message)

            await self.process_message(outbound_message)

            await self.pubsub.ack_message(channel_id, message_id)

    async def get_content_size(self, url: str) -> int:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as head:
                    self.logger.debug("Got head for %s, %s, %s", url, head.status, head.content_length)
                    if head.status <= 204:
                        return head.content_length or 0
                    else:
                        raise ProcessingError(f"Unexpected status code {head.status}")
        except aiohttp.ClientError as ex:
            raise ProcessingError("Failed to get content_size") from ex

    async def prepare_video(self, media_item: MediaItem) -> Tuple[str | None, bytes | None]:

        self.logger.debug("Will look for suitable video in %s", media_item.urls)

        audio_content_size = 0
        if media_item.audio:
            try:
                audio_content_size = await self.get_content_size(media_item.audio) or 0
                self.logger.debug("audio size is %s", audio_content_size)
            except ProcessingError as ex:
                self.logger.warning(f"Ignoring audio channel because of processing error {ex}")
        for video_url in reversed(media_item.urls):
            sz = await self.get_content_size(video_url)
            self.logger.debug("Candidate size is %s", sz)
            if audio_content_size == 0 and sz < self.MAX_URL_SIZE:
                return video_url, None
            elif sz + audio_content_size < self.MAX_UPLOAD_SIZE:
                return None, await self.merge_and_read(video_url, media_item.audio)
        else:
            self.logger.warning("Could not find suitable video/audio")
            return None, None

    async def merge_and_read(self, video_url: str, audio_url: str | None) -> bytes:

        with tempfile.TemporaryDirectory() as d:
            filename = os.path.join(d, str(uuid.uuid4()) + ".mp4")
            self.logger.debug("Going to run ffmpeg for %s, %s, output: %s", video_url, audio_url, filename)
            cmd = f'ffmpeg -i "{video_url}" '
            if audio_url:
                cmd += f'-i "{audio_url}" '

            cmd += f'-shortest -y "{filename}"'

            proc = await asyncio.create_subprocess_shell(cmd)
            try:
                rc = await asyncio.wait_for(proc.wait(), 600)
            except asyncio.TimeoutError:
                self.logger.error("Timeout waiting for ffmpeg, killing")
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except:
                    proc.kill()
                raise ProcessingError("ffmpeg process timeout")
            if rc != 0:
                raise ProcessingError("Non zero rc code for ffmpeg %s", rc)
            with open(filename, "rb") as f:
                return f.read()

    async def process_message(self, message: OutboundMessage):
        try:
            if message.text:
                for chat_id in message.conversation_ids:
                    try:
                        await self.tg_client.send_message(chat_id, message.text)
                    except (TelegramClientBadRequest, TelegramClientForbidden) as ex:
                        self.logger.warning(f"Could not send text to chat {chat_id}, {ex}")

            post = message.post
            if not post:
                return

            caption = f'<a href="{post.original_url}">{post.source_text or post.source_id}</a>: ' \
                      f'<a href="{post.url}">{post.text or "..."}</a>'

            if post.images and len(post.images) > 1:
                if len(post.images) > 10:
                    src = random.sample(post.images, k=10)
                else:
                    src = post.images
                media = [
                    InputMedia(
                        type="photo",
                        media=image.urls[-1],
                        caption=image.caption or caption,
                        parse_mode="HTML") for image in src]

                # copyMessage does not work with media groups
                for chat_id in message.conversation_ids:
                    try:
                        await self.tg_client.send_media_group(chat_id, media)
                    except (TelegramClientBadRequest, TelegramClientForbidden) as ex:
                        self.logger.warning(f"Could not send media group to chat {chat_id}, {ex}")

            reply: Message | None = None
            for index, first_chat_id in enumerate(message.conversation_ids):
                try:
                    if post.videos:
                        # todo: multiple videos?
                        video_url, video_data = await self.prepare_video(post.videos[0])
                        if video_url:
                            reply = await self.tg_client.send_video(first_chat_id,
                                                                    caption=post.videos[0].caption or caption,
                                                                    video_url=video_url)
                        elif video_data:
                            reply = await self.tg_client.send_video(first_chat_id,
                                                                    caption=post.videos[0].caption or caption,
                                                                    video_bytes=video_data)

                    if post.images and len(post.images) == 1:
                        reply = await self.tg_client.send_photo(first_chat_id,
                                                                caption=post.images[0].caption or caption,
                                                                photo_url=post.images[0].urls[-1])
                except (TelegramClientBadRequest, TelegramClientForbidden) as ex:
                    self.logger.warning(f"Could not send msg to {first_chat_id}, {ex}")
                    continue

                if reply:
                    for chat_id in message.conversation_ids[index+1:]:
                        try:
                            await self.tg_client.copy_message(chat_id, first_chat_id, reply.message_id)
                        except (TelegramClientBadRequest, TelegramClientForbidden) as ex:
                            self.logger.warning(f"Could not copy message to {chat_id}, {ex}")
                break

        except ProcessingError:
            self.logger.exception("Could not process the post")


async def main():
    token = get_settings().bot_token
    messenger = TelegramMessenger(token)
    await messenger.serve()


if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    asyncio.run(main())
