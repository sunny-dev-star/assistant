"""
消息实体 (Message Entity)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class Message:
    """消息实体"""
    
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    conversation_id: str = ""
    tenant_id: str = ""
    
    role: str = "user"  # user / assistant / system / tool
    name: Optional[str] = None  # 支持群聊场景等区分不同用户
    content: str = ""
    content_type: str = "text"  # text / image / voice / file / tool_calls
    
    tool_calls: Optional[List[Dict[str, Any]]] = None # 当 role=assistant 且调用了工具时
    tool_call_id: Optional[str] = None # 当 role=tool 时，关联的 tool_call_id
    
    tokens_used: int = 0
    skill_used: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "tenant_id": self.tenant_id,
            "role": self.role,
            "name": self.name,
            "content": self.content,
            "content_type": self.content_type,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "tokens_used": self.tokens_used,
            "skill_used": self.skill_used,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def create_user_message(
        cls,
        conversation_id: str,
        tenant_id: str,
        content: str,
        name: Optional[str] = None,
        content_type: str = "text",
        metadata: Dict[str, Any] = None
    ) -> "Message":
        """创建用户消息"""
        return cls(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role="user",
            name=name,
            content=content,
            content_type=content_type,
            metadata=metadata or {}
        )
    
    @classmethod
    def create_assistant_message(
        cls,
        conversation_id: str,
        tenant_id: str,
        content: str = "",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tokens_used: int = 0,
        skill_used: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> "Message":
        """创建助手消息"""
        return cls(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role="assistant",
            content=content,
            content_type="tool_calls" if tool_calls else "text",
            tool_calls=tool_calls,
            tokens_used=tokens_used,
            skill_used=skill_used,
            metadata=metadata or {}
        )
        
    @classmethod
    def create_tool_message(
        cls,
        conversation_id: str,
        tenant_id: str,
        tool_call_id: str,
        content: str,
        name: str,
        metadata: Dict[str, Any] = None
    ) -> "Message":
        """创建工具结果消息"""
        return cls(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role="tool",
            name=name,
            tool_call_id=tool_call_id,
            content=content,
            metadata=metadata or {}
        )
