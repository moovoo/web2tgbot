import pytest

from bot.scrap.reddit import RedditPosts, RedditThrottleError, RedditNotFoundError
from bot.scrap.reddit_models import SubredditListing, Item


@pytest.mark.asyncio
async def test_get_posts():
    posts = RedditPosts()

    l1 = SubredditListing.from_url("https://reddit.com/r/pics/top/?t=year")
    result = await posts.get_posts(l1)

    assert type(result) is list
    assert len(result) == 25
    assert type(result[0]) is Item


@pytest.mark.asyncio
async def test_get_posts_throttle():
    posts = RedditPosts()
    l1 = SubredditListing.from_url("https://reddit.com/r/throttle/")
    with pytest.raises(RedditThrottleError):
        await posts.get_posts(l1)


@pytest.mark.asyncio
async def test_get_posts_not_found():
    posts = RedditPosts()
    l1 = SubredditListing.from_url("https://reddit.com/r/notfound/")
    with pytest.raises(RedditNotFoundError):
        await posts.get_posts(l1)
