"""
对话相关的 DTO
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ChatRequestDTO:
    """对话请求 DTO"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    channel: str = "web"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatResponseDTO:
    """对话响应 DTO"""
    session_id: str
    message_id: str
    reply: str
    skill_used: Optional[str] = None
    tokens_used: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConversationDTO:
    """会话 DTO"""
    id: str
    tenant_id: str
    user_id: str
    channel: str
    status: str
    created_at: str
    updated_at: str


@dataclass
class MessageDTO:
    """消息 DTO"""
    id: str
    conversation_id: str
    role: str
    content: str
    content_type: str
    tokens_used: int
    skill_used: Optional[str]
    created_at: str
