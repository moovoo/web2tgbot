from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from bot.common.settings import get_settings

engine = create_async_engine(get_settings().db, pool_pre_ping=True, pool_recycle=10*60)

async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)
