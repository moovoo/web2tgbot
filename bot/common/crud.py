from typing import List

from sqlalchemy import select, delete
from sqlalchemy.cimmutabledict import immutabledict
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.common.db_models import MediaSource, Conversation


class DBException(Exception):
    pass


class DBNotFoundException(DBException):
    pass


async def find_or_add_media_source(db: AsyncSession, media_source: str):
    statement = select(MediaSource) \
        .filter(MediaSource.media_source == media_source) \
        .options(selectinload(MediaSource.conversation))
    res = await db.execute(statement)
    if o := res.scalars().first():
        return o

    media_source = MediaSource(
        media_source=media_source
    )
    db.add(media_source)
    await db.commit()
    return media_source


async def get_media_sources(db: AsyncSession) -> List[str]:
    statement = select(MediaSource)
    res = await db.execute(statement)
    return [item.media_source for item in res.scalars().all()]


async def delete_media_source(db: AsyncSession, media_source: str):
    statement = delete(MediaSource) \
        .filter(MediaSource.media_source == media_source)
    res: CursorResult = await db.execute(statement)
    await db.commit()
    if res.rowcount != 1:
        raise DBException("Not found")


async def add_conversation_for_media_source(db: AsyncSession,
                                            conversation: str,
                                            media_source: MediaSource) -> Conversation:
    conv = Conversation(
        conversation=conversation,
    )
    conv.media_source = media_source
    db.add(conv)
    await db.commit()
    return conv


async def get_conversations_for_media_source(db: AsyncSession, media_source: str):
    statement = select(MediaSource) \
        .filter(MediaSource.media_source == media_source) \
        .options(selectinload(MediaSource.conversation))
    res = await db.execute(statement)

    ms: MediaSource = res.scalars().first()

    return [item.conversation for item in ms.conversation]


async def delete_conversation_for_media_source(db: AsyncSession, media_source: str, conversation: str):
    statement = delete(Conversation).where(
        Conversation.conversation == conversation,
        Conversation.media_source.has(MediaSource.media_source == media_source),
    )

    res: CursorResult = await db.execute(statement, execution_options=immutabledict({"synchronize_session": 'fetch'}))
    await db.commit()
    if res.rowcount != 1:
        raise DBException("Not found")


async def get_media_sources_for_conversation(db: AsyncSession, conversation: str):
    statement = select(MediaSource).filter(
        MediaSource.conversation.any(Conversation.conversation == conversation)
    )
    res = await db.execute(statement)
    return [item.media_source for item in res.scalars().all()]
