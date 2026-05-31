"""
配额值对象 (Quota Value Object)
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class Quota:
    """配额值对象"""
    
    limit: int = 100000  # 总配额
    used: int = 0        # 已使用
    
    def has_enough(self, tokens: int) -> bool:
        """检查是否有足够配额"""
        return (self.used + tokens) <= self.limit
    
    def remaining(self) -> int:
        """剩余配额"""
        return max(0, self.limit - self.used)
    
    def usage_percentage(self) -> float:
        """使用百分比"""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100
    
    def consume(self, tokens: int) -> "Quota":
        """消耗配额，返回新的配额对象（值对象不可变）"""
        return Quota(
            limit=self.limit,
            used=self.used + tokens
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining(),
            "percentage": round(self.usage_percentage(), 2)
        }
    
    @classmethod
    def default(cls) -> "Quota":
        """默认配额"""
        return cls(limit=100000, used=0)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Quota":
        """从字典创建"""
        return cls(
            limit=data.get("limit", 100000),
            used=data.get("used", 0)
        )
