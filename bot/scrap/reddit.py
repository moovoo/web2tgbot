import re
from logging import getLogger
from typing import List
import urllib.parse
import pydantic
from prometheus_client import Histogram, Counter

from bot.common.models import Post, MediaItem, ScrapSource
from bot.scrap.reddit_models import RedditReply, Item, RedditPost, PreviewImage, RedditVideoPreview
from bot.scrap.basescrapper import BaseScrapper, ScrapValidationError


class RedditPosts(BaseScrapper):
    REQUEST_TIME = Histogram(name="reddit_client_request_time", documentation="Time spent waiting for reddit client request")
    REQUEST_ERRORS = Counter(name="reddit_client_errors", documentation="Reddit client errors",
                                labelnames=["error_type", "sub_name"])

    def data_to_posts(self, sub: ScrapSource, data: str) -> List[Post]:
        try:
            reply: RedditReply = RedditReply.model_validate_json(data)
        except pydantic.ValidationError as ex:
            self.REQUEST_ERRORS.labels(error_type=f"validation_error", sub_name=sub.params.to_str_tuple()).inc()
            self.logger.error(f"Data were {data}")
            self.logger.error(ex.errors())
            self.logger.error(ex.json())
            raise ScrapValidationError("Could not parse reddit output") from ex
        reddit_posts = reply.data.children if reply.data.children else []

        return [self.reddit_post_to_message(sub.to_str_tuple(), reddit_post.data) for reddit_post in reddit_posts]

    def reddit_post_to_message(self, source_id: str, reddit_post: RedditPost) -> Post:
        images = []
        videos = []
        # audio = None
        if reddit_post.crosspost_parent_list:
            reddit_post = reddit_post.crosspost_parent_list[0]

        if reddit_post.media_metadata:
            # gallery post
            media_items = {}
            for media_id, media_metadata in reddit_post.media_metadata.items():
                if media_metadata.s:
                    # Image|AnimatedImage, url
                    media_items[media_id] = media_metadata.e, media_metadata.s.u or media_metadata.s.mp4

            if reddit_post.gallery_data and reddit_post.gallery_data.items:
                for item in reddit_post.gallery_data.items:
                    try:
                        media_item_type, url = media_items[item.media_id]
                    except KeyError:
                        self.logger.warning("Could not find '%s' in media items", item.media_id)
                        continue
                    item_to_add = MediaItem(
                            urls=[self.fix_url(url)],
                            caption=item.caption
                        )
                    if media_item_type == "Image":
                        images.append(item_to_add)
                    elif media_item_type == "AnimatedImage":
                        videos.append(item_to_add)

        elif (reddit_post.media and reddit_post.media.reddit_video) \
                or (reddit_post.preview and reddit_post.preview.reddit_video_preview):
            video: RedditVideoPreview | None = None
            # todo: parse real xml from dash_url
            if reddit_post.media and reddit_post.media.reddit_video:
                video = reddit_post.media.reddit_video
            elif reddit_post.preview and reddit_post.preview.reddit_video_preview:
                video = reddit_post.preview.reddit_video_preview

            if video:
                resolutions = ["240", "270", "360", "480", "720", "1080"]

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
                        self.logger.warning("Could not find '%s' in resolutions", fallback_filename)
                        video_variants.append(video.fallback_url)
                    videos.append(MediaItem(
                        urls=video_variants,
                        audio=f"{parsed.scheme}://{parsed.netloc}{base_path}/DASH_AUDIO_64.mp4" if not video.is_gif else None))

        elif reddit_post.media and reddit_post.media.type_:
            if reddit_post.media.type_ == "youtube.com" and \
                    reddit_post.media.oembed and reddit_post.media.oembed.thumbnail_url:
                images.append(MediaItem(urls=[reddit_post.media.oembed.thumbnail_url]))
            elif reddit_post.media.type_ == "gfycat.com":
                # todo:
                print("gfycat")
        elif "imgur.com" in reddit_post.url and reddit_post.url.endswith(".gifv"):
            videos.append(MediaItem(
                          urls=[reddit_post.url.replace(".gifv", ".mp4")]))
        elif reddit_post.preview and reddit_post.preview.images:
            # post with images
            post_images: List[PreviewImage] = reddit_post.preview.images
            for post_image in post_images:
                if post_image.variants and (post_image.variants.mp4 or post_image.variants.gif):
                    src = post_image.variants.mp4 or post_image.variants.gif
                    if src and src.resolutions and src.source and src.source.url:
                        this_video = [self.fix_url(res.url) for res in src.resolutions] + [self.fix_url(src.source.url)]
                        videos.append(MediaItem(urls=this_video))
                else:
                    if post_image.source and post_image.source.url:
                        images.append(MediaItem(urls=[self.fix_url(post_image.source.url)]))

        return Post(unique_id=reddit_post.id,
                    source_id=source_id,
                    source_text=reddit_post.subreddit_name_prefixed or reddit_post.subreddit,
                    url=reddit_post.url,
                    text=reddit_post.title,
                    images=images if images else None,
                    videos=videos if videos else None,
                    original_url="https://reddit.com" + reddit_post.permalink,
                    text_block=reddit_post.selftext)
