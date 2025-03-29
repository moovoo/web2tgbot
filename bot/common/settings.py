from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_URL: str = "https://api.telegram.org/bot"
    RD_BASE_URL: str = "https://reddit.com/r/"
    INSTA_BASE_URL: str = "https://www.instagram.com/"
    INSTA_API_BASE_URL: str = "https://i.instagram.com/"

    redis: str = "redis://localhost:6379/"
    rabbitmq: str = "amqp://web2tg:bot@localhost:5672/"
    db: str = "postgresql+asyncpg://web2tg:bot@localhost:5432/web2tg"

    bot_token: str = ""

    max_sources: int = 10

    def sync_db(self):
        return self.db.replace("postgresql+asyncpg", "postgresql+psycopg2")


@lru_cache
def get_settings():
    return Settings()
