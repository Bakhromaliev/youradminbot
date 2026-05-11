from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "bot_users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    username = Column(String)
    bot_language = Column(String, default="uz")
    is_admin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    is_vip = Column(Boolean, default=False)
    vip_until = Column(DateTime)
    daily_post_count = Column(Integer, default=0)
    last_post_date = Column(String)
    admin_channel_id = Column(String)
    admin_channel_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Source(Base):
    __tablename__ = "bot_sources"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("bot_users.id", ondelete="CASCADE"))
    source_id = Column(String)
    source_name = Column(String)
    source_type = Column(String)
    
    links = relationship("SourceChannelLink", back_populates="source", cascade="all, delete-orphan")
    pending_posts = relationship("PendingPost", back_populates="source", cascade="all, delete-orphan")

class OutputChannel(Base):
    __tablename__ = "bot_output_channels"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("bot_users.id", ondelete="CASCADE"))
    channel_id = Column(String)
    channel_name = Column(String)
    target_lang = Column(String, default="uz")
    alphabet = Column(String, default="latin")
    signature = Column(Text)
    is_bold_signature = Column(Boolean, default=True)
    signature_spacing = Column(Integer, default=1)
    
    links = relationship("SourceChannelLink", back_populates="output_channel", cascade="all, delete-orphan")

class SourceChannelLink(Base):
    __tablename__ = "bot_source_links"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("bot_users.id", ondelete="CASCADE"))
    source_id = Column(Integer, ForeignKey("bot_sources.id", ondelete="CASCADE"))
    source_channel_id = Column(String)
    channel_db_id = Column(Integer, ForeignKey("bot_output_channels.id", ondelete="CASCADE"))
    
    source = relationship("Source", back_populates="links")
    output_channel = relationship("OutputChannel", back_populates="links")
    pending_posts = relationship("PendingPost", back_populates="link", cascade="all, delete-orphan")

class PendingPost(Base):
    __tablename__ = "bot_pending_posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("bot_users.id", ondelete="CASCADE"))
    source_id = Column(Integer, ForeignKey("bot_sources.id", ondelete="CASCADE"))
    link_id = Column(Integer, ForeignKey("bot_source_links.id", ondelete="CASCADE"), nullable=True)
    source_type = Column(String)
    original_text = Column(Text)
    translated_text = Column(Text)
    media_url = Column(String)
    media_group_id = Column(String) 
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    source = relationship("Source", back_populates="pending_posts")
    link = relationship("SourceChannelLink", back_populates="pending_posts")
    media = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan")

class PostMedia(Base):
    __tablename__ = "bot_post_media"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("bot_pending_posts.id", ondelete="CASCADE"))
    file_id = Column(String)
    media_type = Column(String)
    
    post = relationship("PendingPost", back_populates="media")
    
class BotSettings(Base):
    __tablename__ = "bot_configs"
    id = Column(Integer, primary_key=True)
    card_number = Column(String, default="8600 0000 0000 0000")
    card_owner = Column(String, default="Falonchi Pistonchiyev")
    vip_price_monthly = Column(Integer, default=50000)
    vip_price_6_months = Column(Integer, default=250000)
    vip_price_yearly = Column(Integer, default=500000)
