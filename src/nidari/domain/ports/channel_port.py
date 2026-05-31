"""
Channel adapter port — unified interface for all inbound channels
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class InboundMessage:
    """Normalized inbound message from any channel"""
    message_id: str
    channel: str  # wechat / feishu / dingtalk / web
    tenant_id: str
    user_id: str
    session_id: str
    content: str
    content_type: str = "text"  # text / image / voice / file / event
    raw: Any = None  # Original platform data for audit


@dataclass
class OutboundMessage:
    """Normalized outbound message to any channel"""
    content: str
    content_type: str = "text"  # text / rich / image
    rich_content: Optional[dict] = None  # WeChat card, Feishu message body, etc.


class IChannelAdapter(ABC):
    """
    Unified channel adapter interface.
    All channels (WeChat, Feishu, DingTalk, etc.) implement this contract.
    """

    @abstractmethod
    async def verify(self, request: Any) -> bool:
        """Verify platform signature (e.g. WeChat sha1, Feishu AES)"""

    @abstractmethod
    async def parse(self, request: Any) -> InboundMessage:
        """Convert platform-specific request to InboundMessage"""

    @abstractmethod
    async def render(self, msg: OutboundMessage, context: dict) -> Any:
        """Convert OutboundMessage to platform-specific response format (XML/JSON)"""

    async def send_proactive(self, user_id: str, msg: OutboundMessage) -> bool:
        """Send proactive message (e.g. daily greetings in elder care).
        Default: not supported, returns False."""
        return False
