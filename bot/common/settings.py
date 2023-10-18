from functools import lru_cache

from pydantic import BaseSettings, RedisDsn, AmqpDsn, PostgresDsn


class Settings(BaseSettings):
    BOT_URL = "https://api.telegram.org/bot"
    RD_BASE_URL = "https://reddit.com/r/"

    redis: RedisDsn = "redis://localhost:6379/"
    rabbitmq: AmqpDsn = "amqp://web2tg:bot@localhost:5672/"
    db: PostgresDsn = "postgresql+asyncpg://web2tg:bot@localhost:5432/web2tg"

    bot_token: str = ""

    max_sources: int = 10

    def sync_db(self):
        return self.db.replace("postgresql+asyncpg", "postgresql+psycopg2")


@lru_cache
def get_settings():
    return Settings()
