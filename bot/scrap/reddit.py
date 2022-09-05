import re
from logging import getLogger
from typing import List
import urllib.parse
import aiohttp
import pydantic

from bot.common.models import Post, MediaItem
from bot.scrap.reddit_models import RedditReply, SubredditListing, Item, RedditPost, PreviewImage, RedditVideoPreview

logger = getLogger()


class RedditError(Exception):
    pass


class RedditThrottleError(RedditError):
    pass


class RedditPosts:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.logger = getLogger()

    async def get_posts(self, sub: SubredditListing) -> List[Item]:
        url = sub.to_url(json=True)

        # todo: more exceptions
        try:
            async with self.session.get(url) as req:
                self.logger.debug("Got reply for %s: %s %s %s",
                                  sub.to_str_tuple(), req.status, req.content_type, req.content_length)
                if not req.ok:
                    if req.status == 429:
                        raise RedditThrottleError("Too many requests")
                    else:
                        raise RedditError(f"Got error {req.status} from {url}")

                data = await req.text()

                reply: RedditReply = pydantic.parse_raw_as(RedditReply, data)

                return reply.data.children if reply.data.children else []
        except aiohttp.ClientError as ex:
            raise RedditError(f"Client error {str(ex)}") from ex


def fix_url(url: str) -> str:
    return url.replace("&amp;", "&")


def reddit_post_to_message(source_id: str, reddit_post: RedditPost) -> Post:
    images = []
    videos = []
    audio = None
    if reddit_post.crosspost_parent_list:
        reddit_post = reddit_post.crosspost_parent_list[0]

    if reddit_post.media_metadata:
        # gallery post
        media_items = {}
        for media_id, media_metadata in reddit_post.media_metadata.items():
            if media_metadata.s and media_metadata.e == "Image":
                media_items[media_id] = media_metadata.s.u

        if reddit_post.gallery_data and reddit_post.gallery_data.items:
            for item in reddit_post.gallery_data.items:
                images.append(MediaItem(
                    urls=[fix_url(media_items[item.media_id])],
                    caption=item.caption
                ))

    elif (reddit_post.media and reddit_post.media.reddit_video) \
            or (reddit_post.preview and reddit_post.preview.reddit_video_preview):
        video: RedditVideoPreview | None = None
        # todo: parse real xml from dash_url
        if reddit_post.media and reddit_post.media.reddit_video:
            video = reddit_post.media.reddit_video
        elif reddit_post.preview and reddit_post.preview.reddit_video_preview:
            video = reddit_post.preview.reddit_video_preview

        if video:
            resolutions = ["240", "360", "480", "720", "1080"]

            parsed = urllib.parse.urlparse(video.fallback_url)
            base_path, fallback_filename = parsed.path.rsplit("/", maxsplit=1)

            match = re.match(r"DASH_(\d+)\.mp4", fallback_filename)
            if match:
                fallback_resolution = match.group(1)
                video_variants = []
                try:
                    for res in resolutions[:resolutions.index(fallback_resolution) + 1]:
                        video_variants.append(f"{parsed.scheme}://{parsed.netloc}{base_path}/DASH_{res}.mp4")
                except (IndexError, ValueError):
                    logger.warning("Could not find '%s' in resolutions", fallback_filename)
                    video_variants.append(video.fallback_url)
                videos.append(MediaItem(
                    urls=video_variants,
                    audio=f"{parsed.scheme}://{parsed.netloc}{base_path}/DASH_audio.mp4" if not video.is_gif else None))

    elif reddit_post.media and reddit_post.media.type_:
        if reddit_post.media.type_ == "youtube.com" and \
                reddit_post.media.oembed and reddit_post.media.oembed.thumbnail_url:
            images.append(MediaItem(urls=[reddit_post.media.oembed.thumbnail_url]))
        elif reddit_post.media.type_ == "gfycat.com":
            # todo:
            print("gfycat")

    elif reddit_post.preview and reddit_post.preview.images:
        # post with images
        post_images: List[PreviewImage] = reddit_post.preview.images
        for post_image in post_images:
            if post_image.variants and (post_image.variants.mp4 or post_image.variants.gif):
                src = post_image.variants.mp4 or post_image.variants.gif
                if src and src.resolutions and src.source and src.source.url:
                    this_video = [fix_url(res.url) for res in src.resolutions] + [fix_url(src.source.url)]
                    videos.append(MediaItem(urls=this_video))
            else:
                if post_image.source and post_image.source.url:
                    images.append(MediaItem(urls=[fix_url(post_image.source.url)]))

    return Post(source_id=source_id,
                source_text=reddit_post.subreddit_name_prefixed or reddit_post.subreddit,
                url=reddit_post.url,
                text=reddit_post.title,
                images=images if images else None,
                videos=videos if videos else None,
                audio=audio,
                original_url="https://reddit.com" + reddit_post.permalink)
