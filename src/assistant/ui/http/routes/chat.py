"""
Chat router - unified endpoint with tenant authentication
"""
import uuid
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ....domain.models.context import TenantContext, LLMConfig
from ....domain.value_objects.channel import Channel
from ....infrastructure.config.settings import settings

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request"""
    message: str
    session_id: Optional[str] = None
    user_id: str = "anonymous"
    user_name: Optional[str] = None
    channel: str = "web"
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response"""
    session_id: str
    reply: str
    tokens_used: int = 0
    cost_usd: float = 0.0


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_req: ChatRequest
):
    """
    Unified chat endpoint.
    Tenant is injected by TenantAuthMiddleware from Bearer token (or default in dev mode).
    """
    app_service = request.app.state.assistant_chat_app_service
    tenant = request.state.tenant

    session_id = chat_req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    user_id = chat_req.user_id

    # Build LLM config from tenant settings + global API key
    default_model = tenant.config.get("default_model", "deepseek/deepseek-chat")
    llm_config = LLMConfig(
        provider="openai_compat",
        model=default_model,
        api_key=settings.DEEPSEEK_API_KEY or None,
        api_base=settings.DEEPSEEK_API_URL if settings.DEEPSEEK_API_URL else None,
    )

    context = TenantContext(
        tenant_id=tenant.id,
        user_id=user_id,
        channel=Channel(chat_req.channel),
        session_id=session_id,
        llm_config=llm_config,
        allowed_skills=tenant.config.get("enabled_skills", []),
        metadata={
            **(chat_req.metadata or {}),
            "window_size": tenant.config.get("window_size", 10),
        }
    )

    result = await app_service.execute(
        context=context,
        user_message_content=chat_req.message,
        user_name=chat_req.user_name
    )

    return ChatResponse(**result)


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    request: Request,
    session_id: str,
    limit: int = 50
):
    """Get chat history for a session"""
    app_service = request.app.state.assistant_chat_app_service
    messages = await app_service.message_repo.list_by_conversation(session_id, limit=limit)

    return {
        "session_id": session_id,
        "messages": [m.to_dict() for m in messages]
    }
