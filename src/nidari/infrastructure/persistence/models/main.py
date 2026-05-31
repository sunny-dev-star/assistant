"""
SQLAlchemy ORM models for all entities
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, BigInteger, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


class TenantModel(Base):
    """Tenants table"""
    __tablename__ = "tenants"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    industry = Column(String(50))
    contact = Column(String(100))
    plan = Column(String(20), default="basic")
    status = Column(String(20), default="active")
    api_key = Column(String(200), unique=True, nullable=False)
    quota_used = Column(Integer, default=0)
    quota_limit = Column(Integer, default=100000)
    config = Column(JSON, default=dict)
    window_size = Column(Integer, default=10)
    default_model = Column(String(50), default="deepseek/deepseek-chat")
    enabled_skills = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = relationship("ConversationModel", back_populates="tenant")


class ConversationModel(Base):
    """Conversations table"""
    __tablename__ = "conversations"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    channel = Column(String(20), default="web")
    status = Column(String(20), default="active")
    extra_data = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    tenant = relationship("TenantModel", back_populates="conversations")
    messages = relationship("MessageModel", back_populates="conversation", order_by="MessageModel.created_at")


class MessageModel(Base):
    """Messages table"""
    __tablename__ = "messages"

    id = Column(String(50), primary_key=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id"), nullable=False, index=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    name = Column(String(100), nullable=True)
    content = Column(Text, default="")
    content_type = Column(String(20), default="text")
    tool_calls = Column(JSON, nullable=True)
    tool_call_id = Column(String(100), nullable=True)
    tokens_used = Column(Integer, default=0)
    skill_used = Column(String(50), nullable=True)
    meta_data = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("ConversationModel", back_populates="messages")


class ApiUsageModel(Base):
    """API usage tracking for billing"""
    __tablename__ = "api_usage"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=False, index=True)
    conversation_id = Column(String(50), nullable=True)
    model = Column(String(50), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(BigInteger, default=0)  # micro-dollars
    skill_name = Column(String(50), nullable=True)
    channel = Column(String(20), default="web")
    created_at = Column(DateTime, default=datetime.utcnow)
