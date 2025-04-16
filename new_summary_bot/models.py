from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    tariff = Column(String, default="free")

    # Храним время рассылки, формат "HH:MM"
    schedule_time = Column(String, nullable=True)
    # Смещение в часах относительно UTC
    user_offset = Column(Integer, default=0)
    user_local_time = Column(String, nullable=True)

    subscription_until = Column(DateTime, nullable=True)
    last_summary_sent = Column(DateTime, nullable=True)

    channels = relationship("Channel", back_populates="user", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="user", cascade="all, delete-orphan")

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_tag = Column(String, nullable=False)

    user = relationship("User", back_populates="channels")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_name = Column(String, nullable=False)

    user = relationship("User", back_populates="topics")

class MessageToAdmin(Base):
    __tablename__ = "messages_to_admin"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_tag = Column(String, nullable=False)
    text = Column(Text, nullable=True)
    link = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
