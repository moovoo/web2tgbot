import os

from bot.common.settings import get_settings


def pytest_configure():
    settings = get_settings()

    try:
        os.environ["RD_BASE_URL"]
    except KeyError:
        settings.RD_BASE_URL = "http://127.0.0.1:8081/r/"

    try:
        os.environ["BOT_URL"]
    except KeyError:
        settings.BOT_URL = "http://127.0.0.1:8082/bot"
