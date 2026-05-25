"""
消息实体 (Message Entity) — 支持多模态 (text / image / voice / file)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class Attachment:
    """消息附件（图片/语音/文件）"""
    type: str = "image"  # image / voice / file
    url: str = ""        # 可访问的 URL
    base64: str = ""     # base64 编码（可选，优先用 url）
    mime_type: str = ""  # image/jpeg, audio/wav, application/pdf 等
    name: str = ""       # 文件名
    size: int = 0        # 字节大小

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": self.type, "url": self.url, "mime_type": self.mime_type,
             "name": self.name, "size": self.size}
        if self.base64:
            d["base64"] = self.base64[:20] + "...(truncated)"  # 存储时截断
        return d

    def to_llm_content(self) -> Dict[str, Any]:
        """构造传给 LLM 的多模态 content 片段"""
        if self.type == "image":
            if self.url:
                return {"type": "image_url", "image_url": {"url": self.url}}
            elif self.base64:
                return {"type": "image_url", "image_url": {
                    "url": f"data:{self.mime_type or 'image/jpeg'};base64,{self.base64}"
                }}
        elif self.type == "file":
            # 文件内容已经提取为文本，放在 content 里
            return {"type": "text", "text": f"[附件: {self.name}]\n{self.url}"}
        return {"type": "text", "text": f"[{self.type}: {self.url}]"}


@dataclass
class Message:
    """消息实体"""

    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    conversation_id: str = ""
    tenant_id: str = ""

    role: str = "user"  # user / assistant / system / tool
    name: Optional[str] = None
    content: str = ""
    content_type: str = "text"  # text / image / voice / file / multimodal / tool_calls

    # 多模态附件列表
    attachments: List[Attachment] = field(default_factory=list)

    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    tokens_used: int = 0
    skill_used: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = {
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
            "created_at": self.created_at.isoformat(),
        }
        if self.attachments:
            d["attachments"] = [a.to_dict() for a in self.attachments]
        return d

    @classmethod
    def create_user_message(
        cls,
        conversation_id: str,
        tenant_id: str,
        content: str,
        name: Optional[str] = None,
        content_type: str = "text",
        attachments: List[Attachment] = None,
        metadata: Dict[str, Any] = None
    ) -> "Message":
        return cls(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role="user",
            name=name,
            content=content,
            content_type=content_type,
            attachments=attachments or [],
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
        return cls(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role="tool",
            name=name,
            tool_call_id=tool_call_id,
            content=content,
            metadata=metadata or {}
        )
