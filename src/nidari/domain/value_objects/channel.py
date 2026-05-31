"""
渠道值对象 (Channel Value Object)
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    """渠道值对象"""
    
    value: str  # wechat / feishu / dingtalk / web / miniapp / app
    
    def is_wechat(self) -> bool:
        return self.value == "wechat"
    
    def is_feishu(self) -> bool:
        return self.value == "feishu"
    
    def is_dingtalk(self) -> bool:
        return self.value == "dingtalk"
    
    def is_web(self) -> bool:
        return self.value == "web"
    
    def is_miniapp(self) -> bool:
        return self.value == "miniapp"
    
    def is_app(self) -> bool:
        return self.value == "app"
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Channel):
            return self.value == other.value
        return self.value == other
    
    def __hash__(self) -> int:
        return hash(self.value)
