"""
Conversation context management domain service
- Configurable sliding window (per-tenant)
- Auto-summarize long conversations
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
        """Build message list for LLM from history"""
        window_size = context.metadata.get("window_size", self.DEFAULT_WINDOW)
        window_size = min(window_size, self.MAX_WINDOW)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Keep last window_size * 2 messages (user + assistant each round)
        history_to_keep = history[-(window_size * 2):]

        for msg in history_to_keep:
            m: Dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                m["name"] = msg.name
            if msg.role == "assistant" and msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            elif msg.role == "tool" and msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            messages.append(m)

        return messages

    def append_user_message(
        self,
        context: TenantContext,
        history: List[Message],
        content: str,
        user_name: str = None
    ) -> Message:
        """Create and append user message"""
        msg = Message.create_user_message(
            conversation_id=context.session_id,
            tenant_id=context.tenant_id,
            content=content,
            name=user_name
        )
        history.append(msg)
        return msg

    async def build_context_with_summary(
        self,
        context: TenantContext,
        history: List[Message],
        system_prompt: str = ""
    ) -> List[Dict[str, Any]]:
        """
        If history exceeds window, summarize older messages into a system message.
        Requires llm_port to be set.
        """
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
            m: Dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                m["name"] = msg.name
            if msg.role == "assistant" and msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            elif msg.role == "tool" and msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            messages.append(m)

        return messages

    async def _summarize(self, messages: List[Message]) -> str:
        """Summarize older messages via LLM"""
        from ..value_objects.channel import Channel
        text_parts = []
        for m in messages:
            prefix = m.name or m.role
            text_parts.append(f"{prefix}: {m.content}")
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
