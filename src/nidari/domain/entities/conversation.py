"""
会话实体 (Conversation Entity)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

from ..value_objects.channel import Channel


@dataclass
class Conversation:
    """会话实体"""
    
    id: str = field(default_factory=lambda: f"conv_{uuid.uuid4().hex[:12]}")
    tenant_id: str = ""
    user_id: str = ""
    channel: Channel = field(default_factory=lambda: Channel("web"))
    
    status: str = "active"  # active / closed / expired
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    def close(self):
        """关闭会话"""
        self.status = "closed"
        self.closed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_metadata(self, key: str, value: Any):
        """更新元数据"""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "channel": self.channel.value,
            "status": self.status,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None
        }
