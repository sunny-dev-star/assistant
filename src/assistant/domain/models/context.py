"""
多租户与会话上下文模型 (Tenant Context)
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from ..value_objects.channel import Channel


@dataclass
class LLMConfig:
    """大模型配置"""
    provider: str = "openai_compat" # openai_compat 等
    model: str = "deepseek-chat"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class TenantContext:
    """贯穿请求链路的租户与用户上下文"""
    
    tenant_id: str
    user_id: str
    channel: Channel
    session_id: str
    
    # 该请求关联的模型配置（解析后合并了租户默认和用户重写）
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    
    # 租户允许的技能列表或白名单
    allowed_skills: List[str] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
