import asyncio
import logging.config
import os
import signal
import tempfile
import uuid
from itertools import batched
from logging import getLogger
from pathlib import Path
from typing import Tuple

from bot.common.models import OutboundMessage, MediaItem
from bot.common.pubsub import get_new_pubsub
from bot.common.settings import get_settings
import telegram

from prometheus_client import Histogram, Counter
from prometheus_async.aio import time, web

class ProcessingError(Exception):
    pass


class TelegramMessenger:

    MAX_URL_SIZE = 20 * 1024 * 1000
    MAX_UPLOAD_SIZE = 50 * 1024 * 1000

    VIDEO_PROCESSING_TIME = Histogram("tg_messenger_video_processing_time", "Time spent processing video")
    MESSAGE_PROCESSING_TIME = Histogram("tg_messenger_message_processing_time", "Time spent processing message")
    MESSAGES_PROCESSED = Counter("tg_messenger_messages_processed", "Number of messages processed",
                                 labelnames=["conversation_id"])

    def __init__(self, token: str):
        self.logger = getLogger()
        self.token = token
        self.bot_id = token.split(":")[0]
        self.pubsub = get_new_pubsub()
        self.tg_client = telegram.Bot(self.token)

    async def serve(self):
        reader = self.pubsub.stream_messages(f"telegram_{self.bot_id}")
        try:
            await self.tg_client.initialize()
            async for channel_id, message_id, message_raw in reader:
                outbound_message: OutboundMessage = OutboundMessage.model_validate_json(message_raw)
                self.logger.debug("Got new message %s", outbound_message)

                await self.process_message(outbound_message)

                for c_id in outbound_message.conversation_ids:
                    self.MESSAGES_PROCESSED.labels(conversation_id=c_id).inc()

                await self.pubsub.ack_message(channel_id, message_id)
        finally:
            await self.tg_client.shutdown()

    def get_content_size(self, path: str) -> int:
        try:
            size = Path(path).stat().st_size
            self.logger.debug("Got size for %s: %s", path, size)
            return size
        except OSError as ex:
            self.logger.error("Failed to get content size for %s: %s", path, ex)
            raise ProcessingError("Failed to get content_size") from ex

    def _cleanup_files(self, post):
        for media_list in (post.images or [], post.videos or []):
            for media_item in media_list:
                for url in media_item.urls:
                    try:
                        if Path(url).exists():
                            Path(url).unlink()
                            self.logger.debug("Deleted %s", url)
                    except OSError as ex:
                        self.logger.warning("Failed to delete %s: %s", url, ex)
                if media_item.audio:
                    try:
                        if Path(media_item.audio).exists():
                            Path(media_item.audio).unlink()
                            self.logger.debug("Deleted %s", media_item.audio)
                    except OSError as ex:
                        self.logger.warning("Failed to delete %s: %s", media_item.audio, ex)

    @time(VIDEO_PROCESSING_TIME)
    async def prepare_video(self, media_item: MediaItem) -> str | bytes | None:
        self.logger.debug("Will look for suitable video in %s", media_item.urls)

        audio_content_size = 0
        if media_item.audio:
            try:
                audio_content_size = self.get_content_size(media_item.audio) or 0
                self.logger.debug("audio size is %s", audio_content_size)
            except ProcessingError as ex:
                self.logger.warning(f"Ignoring audio channel because of processing error {ex}")
        for video_url in reversed(media_item.urls):
            sz = self.get_content_size(video_url)
            self.logger.debug("Candidate size is %s", sz)
            if audio_content_size == 0 and sz < self.MAX_URL_SIZE:
                return video_url
            elif sz + audio_content_size < self.MAX_UPLOAD_SIZE:
                return await self.merge_and_read(video_url, media_item.audio)
        else:
            self.logger.warning("Could not find suitable video/audio")
            return None

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

    @time(MESSAGE_PROCESSING_TIME)
    async def process_message(self, message: OutboundMessage):
        try:
            if message.text:
                for chat_id in message.conversation_ids:
                    try:
                        await self.tg_client.send_message(chat_id, message.text, parse_mode="HTML")
                    except (telegram.error.BadRequest, telegram.error.Forbidden) as ex:
                        self.logger.warning(f"Could not send text to chat {chat_id}, {ex}")

            post = message.post
            if not post:
                return

            caption = f'<a href="{post.original_url}">{post.source_text or post.source_id}</a>: ' \
                      f'<a href="{post.url}">{post.text or "..."}</a>'
            if post.text_block:
                caption += f'<blockquote expandable>{post.text_block[:800]}</blockquote>'

            if post.images and len(post.images) > 1:
                with_parts = len(post.images) > 10
                for i, image_group in enumerate(batched(post.images, 10)):
                    suffix = f"\n\nPart #{i+1}" if with_parts else ""
                    media = [
                        telegram.InputMediaPhoto(
                            media=open(image.urls[-1], "rb"),
                            caption=f"{image.caption or caption}{suffix}",
                            parse_mode="HTML") for image in image_group]

                    # copyMessage does not work with media groups
                    for chat_id in message.conversation_ids:
                        try:
                            await self.tg_client.send_media_group(chat_id, media)
                        except (telegram.error.BadRequest, telegram.error.Forbidden) as ex:
                            self.logger.warning(f"Could not send media group to chat {chat_id}, {ex}")

            reply: telegram.Message | None = None
            for index, first_chat_id in enumerate(message.conversation_ids):
                try:
                    if post.videos:
                        # todo: multiple videos?
                        video = await self.prepare_video(post.videos[0])
                        if video:
                            await self.tg_client.send_video(
                                chat_id=first_chat_id,
                                video=video if type(video) is bytes else open(video, "rb"),
                                caption=post.videos[0].caption or caption,
                                parse_mode="HTML"
                            )

                    if post.images and len(post.images) == 1:
                        reply = await self.tg_client.send_photo(chat_id=first_chat_id,
                                                                photo=open(post.images[0].urls[-1], "rb"),
                                                                caption=post.images[0].caption or caption,
                                                                parse_mode="HTML"
                                                                )
                except (telegram.error.BadRequest, telegram.error.Forbidden) as ex:
                    self.logger.warning(f"Could not send msg to {first_chat_id}, {ex}")
                    continue

                if reply:
                    for chat_id in message.conversation_ids[index+1:]:
                        try:
                            await self.tg_client.copy_message(chat_id=chat_id,
                                                              from_chat_id=first_chat_id,
                                                              message_id=reply.message_id)
                        except (telegram.error.BadRequest, telegram.error.Forbidden) as ex:
                            self.logger.warning(f"Could not copy message to {chat_id}, {ex}")
                break

        except ProcessingError:
            self.logger.exception("Could not process the post")
        finally:
            if message.post:
                self._cleanup_files(message.post)


async def main():
    _ = await web.start_http_server(port=8000)
    token = get_settings().bot_token
    messenger = TelegramMessenger(token)
    await messenger.serve()


if __name__ == "__main__":
    logging.config.fileConfig("logger.ini")
    asyncio.run(main())
