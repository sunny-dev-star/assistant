"""
Conversation context management domain service
- Configurable sliding window (per-tenant)
- Auto-summarize long conversations
- Multimodal message support (image/voice/file attachments)
"""
from typing import List, Dict, Any

from ..models.context import TenantContext
from ..entities.message import Message


class ConversationContextService:
    """Context window management"""

    DEFAULT_WINDOW = 10
    MAX_WINDOW = 50

    def __init__(self, llm_port=None):
        self.llm_port = llm_port

    def build_context_messages(
        self,
        context: TenantContext,
        history: List[Message],
        system_prompt: str = ""
    ) -> List[Dict[str, Any]]:
        """Build message list for LLM from history — supports multimodal"""
        window_size = context.metadata.get("window_size", self.DEFAULT_WINDOW)
        window_size = min(window_size, self.MAX_WINDOW)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        history_to_keep = history[-(window_size * 2):]

        for msg in history_to_keep:
            m = self._message_to_llm_dict(msg)
            messages.append(m)

        return messages

    def _message_to_llm_dict(self, msg: Message) -> Dict[str, Any]:
        """
        将 Message 实体转为 LLM API 消息格式。
        支持纯文本和多模态（带附件）消息。
        """
        # tool 消息特殊格式
        if msg.role == "tool":
            m = {"role": "tool", "content": msg.content}
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            return m

        # assistant 消息
        if msg.role == "assistant":
            m = {"role": "assistant", "content": msg.content or None}
            if msg.name:
                m["name"] = msg.name
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
                m["content"] = None  # tool_calls 时 content 通常为 null
            return m

        # user 消息：检查是否有附件
        if msg.role == "user" and msg.attachments:
            return self._build_multimodal_user_message(msg)

        # 纯文本 user / system
        m = {"role": msg.role, "content": msg.content}
        if msg.name:
            m["name"] = msg.name
        return m

    def _build_multimodal_user_message(self, msg: Message) -> Dict[str, Any]:
        """
        构建多模态 user 消息（OpenAI vision 格式）。
        content 从 string 变为 list[dict]：
        [
          {"type": "text", "text": "描述一下这张图片"},
          {"type": "image_url", "image_url": {"url": "https://..."}}
        ]
        """
        content_parts = []

        # 文本部分
        if msg.content:
            content_parts.append({"type": "text", "text": msg.content})

        # 附件部分
        for attachment in msg.attachments:
            llm_content = attachment.to_llm_content()
            content_parts.append(llm_content)

        if not content_parts:
            content_parts.append({"type": "text", "text": ""})

        m = {"role": "user", "content": content_parts}
        if msg.name:
            m["name"] = msg.name
        return m

    def append_user_message(
        self,
        context: TenantContext,
        history: List[Message],
        content: str,
        user_name: str = None,
        attachments: list = None,
    ) -> Message:
        """Create and append user message (supports attachments)"""
        content_type = "text"
        if attachments:
            has_image = any(a.type == "image" for a in attachments)
            has_voice = any(a.type == "voice" for a in attachments)
            if has_image:
                content_type = "multimodal"
            elif has_voice:
                content_type = "voice"

        msg = Message.create_user_message(
            conversation_id=context.session_id,
            tenant_id=context.tenant_id,
            content=content,
            name=user_name,
            content_type=content_type,
            attachments=attachments,
        )
        history.append(msg)
        return msg

    async def build_context_with_summary(
        self,
        context: TenantContext,
        history: List[Message],
        system_prompt: str = ""
    ) -> List[Dict[str, Any]]:
        """If history exceeds window, summarize older messages"""
        if not self.llm_port or len(history) <= self.DEFAULT_WINDOW * 2:
            return self.build_context_messages(context, history, system_prompt)

        window_size = context.metadata.get("window_size", self.DEFAULT_WINDOW)
        cutoff = len(history) - window_size * 2
        older = history[:cutoff]
        recent = history[cutoff:]

        summary = await self._summarize(older)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "system", "content": f"[Conversation Summary] {summary}"})

        for msg in recent:
            m = self._message_to_llm_dict(msg)
            messages.append(m)

        return messages

    async def _summarize(self, messages: List[Message]) -> str:
        """Summarize older messages via LLM"""
        from ..value_objects.channel import Channel
        text_parts = []
        for m in messages:
            prefix = m.name or m.role
            text_parts.append(f"{prefix}: {m.content[:200]}")
        text = "\n".join(text_parts)[-2000:]

        temp_ctx = TenantContext(
            tenant_id="system",
            user_id="system",
            channel=Channel("web"),
            session_id="summary",
        )
        response = await self.llm_port.chat(
            context=temp_ctx,
            messages=[
                {"role": "system", "content": "Compress the following conversation into a brief summary, keeping key facts, decisions, and context."},
                {"role": "user", "content": text}
            ],
        )
        return response.content if response.content else "Previous conversation summarized."
