"""
多租户与会话上下文模型 (Tenant Context)
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from ..value_objects.channel import Channel


@dataclass
class LLMConfig:
    """大模型配置"""
    provider: str = "openai_compat"
    model: str = "deepseek-chat"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048

    # 视觉模型（图片理解），留空则使用主模型（如果主模型支持 vision）
    vision_model: Optional[str] = None
    vision_api_key: Optional[str] = None
    vision_api_base: Optional[str] = None

    # 语音转文字模型配置
    stt_provider: Optional[str] = None   # "whisper" / "aliyun" / "tencent" 等
    stt_api_key: Optional[str] = None
    stt_api_base: Optional[str] = None
    stt_model: Optional[str] = None      # "whisper-1" 等


@dataclass
class TenantContext:
    """贯穿请求链路的租户与用户上下文"""

    tenant_id: str
    user_id: str
    channel: Channel
    session_id: str

    llm_config: LLMConfig = field(default_factory=LLMConfig)
    allowed_skills: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
