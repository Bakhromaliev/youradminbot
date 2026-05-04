from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    bot_language = Column(String, default="uz")
    is_admin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    is_vip = Column(Boolean, default=False) # VIP maqomi
    vip_until = Column(DateTime) # VIP muddati
    daily_post_count = Column(Integer, default=0) # Bugungi postlar soni
    last_post_date = Column(String) # Oxirgi post sanasi (limitni yangilash uchun)
    created_at = Column(DateTime, default=datetime.utcnow)

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_id = Column(String) # @username or ID
    source_name = Column(String)
    source_type = Column(String) # telegram, twitter
    
    links = relationship("SourceChannelLink", back_populates="source", cascade="all, delete-orphan")

class OutputChannel(Base):
    __tablename__ = "output_channels"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    channel_id = Column(String)
    channel_name = Column(String)
    target_lang = Column(String, default="uz")
    alphabet = Column(String, default="latin")
    signature = Column(Text)
    is_bold_signature = Column(Boolean, default=True)
    signature_spacing = Column(Integer, default=1)
    
    links = relationship("SourceChannelLink", back_populates="output_channel")

class SourceChannelLink(Base):
    __tablename__ = "source_channel_links"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_id = Column(Integer, ForeignKey("sources.id")) # Source ID ga bog'lanadi
    source_channel_id = Column(String) # Monitor uchun @username
    channel_db_id = Column(Integer, ForeignKey("output_channels.id"))
    
    source = relationship("Source", back_populates="links")
    output_channel = relationship("OutputChannel", back_populates="links")

class PendingPost(Base):
    __tablename__ = "pending_posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    link_id = Column(Integer, ForeignKey("source_channel_links.id"))
    source_type = Column(String)
    original_text = Column(Text)
    translated_text = Column(Text)
    media_url = Column(String)
    media_group_id = Column(String) 
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    media = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan")

class PostMedia(Base):
    __tablename__ = "post_media"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("pending_posts.id"))
    file_id = Column(String)
    media_type = Column(String)
    
    post = relationship("PendingPost", back_populates="media")
    
class BotSettings(Base):
    __tablename__ = "bot_settings"
    id = Column(Integer, primary_key=True)
    card_number = Column(String, default="8600 0000 0000 0000")
    card_owner = Column(String, default="Falonchi Pistonchiyev")
    vip_price_monthly = Column(Integer, default=50000) # So'mda
    vip_price_6_months = Column(Integer, default=250000) # So'mda
    vip_price_yearly = Column(Integer, default=500000) # So'mda
