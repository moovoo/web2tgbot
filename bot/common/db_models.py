from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from bot.db.base_class import Base


class MediaSource(Base):
    __tablename__ = "media_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_source = Column(String, index=True, unique=True)

    conversation = relationship("Conversation", back_populates="media_source", cascade="all, delete")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation = Column(String, index=True)

    media_source_id = Column(Integer, ForeignKey("media_sources.id", ondelete="CASCADE"))
    media_source = relationship("MediaSource", back_populates="conversation")
