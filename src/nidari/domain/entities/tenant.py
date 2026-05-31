"""
租户实体 (Tenant Entity)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from ..value_objects.api_key import ApiKey
from ..value_objects.quota import Quota


@dataclass
class Tenant:
    """租户实体"""
    
    id: str = field(default_factory=lambda: f"tnt_{uuid.uuid4().hex[:12]}")
    name: str = ""
    industry: Optional[str] = None
    contact: Optional[str] = None
    plan: str = "basic"  # basic / professional / enterprise
    status: str = "active"  # active / suspended / deleted
    
    api_key: ApiKey = field(default_factory=ApiKey.generate)
    quota: Quota = field(default_factory=Quota.default)
    
    config: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_active(self) -> bool:
        """检查租户是否活跃"""
        return self.status == "active"
    
    def has_quota(self, tokens: int) -> bool:
        """检查是否有足够配额"""
        return self.quota.has_enough(tokens)
    
    def consume_quota(self, tokens: int):
        """消耗配额"""
        self.quota.consume(tokens)
        self.updated_at = datetime.utcnow()
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)
        self.updated_at = datetime.utcnow()
    
    def suspend(self):
        """暂停租户"""
        self.status = "suspended"
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """激活租户"""
        self.status = "active"
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "industry": self.industry,
            "contact": self.contact,
            "plan": self.plan,
            "status": self.status,
            "api_key": self.api_key.value,
            "quota": self.quota.to_dict(),
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
