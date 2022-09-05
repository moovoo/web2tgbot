import pydantic

from bot.reddit_scrapper import reddit_post_to_message
from bot.scrap.reddit_models import Item, RedditReply


def parse(filename: str) -> Item:
    reply = pydantic.parse_file_as(RedditReply, filename)
    return reply.data.children[0]


def test_post_with_image_gallery():
    # https://www.reddit.com/r/pics/comments/vxdrjs/the_first_fullcolor_images_from_the_james_webb/.json
    data = parse("_post_image_gallery.json")
    post = reddit_post_to_message("source", data.data)

    assert post.text == "The first full-color images from the James Webb Space Telescope [OC]"
    assert post.url == "https://www.reddit.com/gallery/vxdrjs"
    assert len(post.images) == 4
    assert post.videos is None
    media_item = post.images[0]
    assert len(media_item.urls) == 1
    assert media_item.urls[0] == "https://preview.redd.it/t6332hcll5b91.jpg?width=2799&format=pjpg&auto=webp&s=f2e3bc697305c5e0d9776c5eb0f61bdaf486b7e6"


def test_post_with_image_gallery_captions():
    # https://www.reddit.com/r/pics/comments/w6yf1u/a_few_glimpses_from_my_visit_to_north_korea/.json
    data = parse("_post_image_gallery_with_captions.json")
    post = reddit_post_to_message("source", data.data)

    assert post.text == "A few glimpses from my visit to North Korea, before coronavirus."
    assert post.url == "https://www.reddit.com/gallery/w6yf1u"

    assert len(post.images) == 20
    assert len(post.images[0].urls) == 1
    assert post.images[0].urls[0] == "https://preview.redd.it/fom6dfijajd91.jpg?width=1920&format=pjpg&auto=webp&s=028dddec12e0e3c0a4ff3325861276f7be412d46"
    assert post.images[0].caption == "At a school for gifted children, in Pyongsong, we were shown an exhibition on taxidermy. The only part of the trip where we could not help but laugh. "


def test_post_single_image_preview():
    # https://www.reddit.com/r/pics/comments/vuz52b/my_client_asked_to_make_this_rug_with_her_rats_oc/.json
    data = parse("_post_single_preview_image.json")
    post = reddit_post_to_message("source", data.data)

    assert post.text == "My client asked to make this rug with her rats [OC]"
    assert post.url == "https://i.redd.it/lszwdbllwia91.jpg"
    assert len(post.images) == 1
    assert post.videos is None
    assert len(post.images[0].urls) == 1
    assert post.images[0].urls[0] == "https://preview.redd.it/lszwdbllwia91.jpg?auto=webp&s=60e553dc2a8e396b3ed372676d5cb205b90252f1"


def test_post_preview_gif():
    # https://www.reddit.com/r/gifs/comments/vvfuts/mobius_strip/.json
    data = parse("_post_preview_gif.json")
    post = reddit_post_to_message("source", data.data)

    assert post.text == "Mobius strip"
    assert post.url == "https://i.redd.it/ildc93m74na91.gif"
    assert post.images is None
    assert len(post.videos) == 1
    media_item = post.videos[0]
    assert len(media_item.urls) == 5
    assert media_item.urls[-1] == "https://preview.redd.it/ildc93m74na91.gif?format=mp4&s=48a695e4753ec7706daf6724bce339100d678e02"


def test_post_media_video():
    # https://www.reddit.com/r/funny/comments/vl646u/our_cat_went_on_a_ventilation_vacation_had_to/.json
    data = parse("_post_media_video.json")
    post = reddit_post_to_message("source", data.data)

    assert post.text == "Our cat went on a ventilation vacation — had to lure her chonkiness out with fancy feast"
    assert post.url == "https://v.redd.it/vllakxmv8z791"
    assert post.images is None
    assert len(post.videos) == 1

    media_item = post.videos[0]
    assert media_item.audio == "https://v.redd.it/vllakxmv8z791/DASH_audio.mp4"

    assert len(media_item.urls) == 4
    assert media_item.urls[-1] == "https://v.redd.it/vllakxmv8z791/DASH_720.mp4"


def test_post_oembed_youtube():
    # https://www.reddit.com/r/videos/comments/vsdzq4/man_explaining_the_different_zulu_clicks_is_the/.json
    data = parse("_post_oembed_youtube.json")
    post = reddit_post_to_message("source", data.data)

    assert post.text == "Man explaining the different Zulu clicks is the best thing you will see today"
    assert post.url == "https://youtu.be/kBW2eDx3h8w"
    assert len(post.images) == 1
    assert len(post.images[0].urls) == 1
    assert post.images[0].urls[0] == "https://i.ytimg.com/vi/kBW2eDx3h8w/hqdefault.jpg"
    assert post.videos is None
