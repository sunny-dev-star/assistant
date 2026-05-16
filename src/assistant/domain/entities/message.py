"""
消息实体 (Message Entity)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


@dataclass
class Message:
    """消息实体"""
    
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    conversation_id: str = ""
    tenant_id: str = ""
    
    role: str = "user"  # user / assistant / system
    content: str = ""
    content_type: str = "text"  # text / image / voice / file
    
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
            "content": self.content,
            "content_type": self.content_type,
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
        content_type: str = "text",
        metadata: Dict[str, Any] = None
    ) -> "Message":
        """创建用户消息"""
        return cls(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role="user",
            content=content,
            content_type=content_type,
            metadata=metadata or {}
        )
    
    @classmethod
    def create_assistant_message(
        cls,
        conversation_id: str,
        tenant_id: str,
        content: str,
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
            tokens_used=tokens_used,
            skill_used=skill_used,
            metadata=metadata or {}
        )
