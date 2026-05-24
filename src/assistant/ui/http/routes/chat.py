"""
对话路由
"""
import uuid
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ....domain.models.context import TenantContext, LLMConfig
from ....domain.value_objects.channel import Channel

router = APIRouter()


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    channel: str = "web"
    tenant_id: str = "default_tenant"
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    reply: str
    tokens_used: int = 0
    cost_usd: float = 0.0


def get_app_service(request: Request):
    """从 app.state 获取 AssistantChatAppService 实例"""
    return request.app.state.assistant_chat_app_service


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_req: ChatRequest
):
    """
    发起对话 (LiteLLM 驱动)
    """
    app_service = get_app_service(request)
    
    # 组装 TenantContext (实际场景中应从 Token 或网关 Header 提取)
    session_id = chat_req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    user_id = chat_req.user_id or f"user_{uuid.uuid4().hex[:8]}"
    
    # TODO: 实际应从租户配置中读取大模型配置
    llm_config = LLMConfig(
        provider="openai_compat",
        model="deepseek/deepseek-chat"
        # api_key="从配置或环境变量加载"
    )
    
    context = TenantContext(
        tenant_id=chat_req.tenant_id,
        user_id=user_id,
        channel=Channel(chat_req.channel),
        session_id=session_id,
        llm_config=llm_config,
        metadata=chat_req.metadata or {}
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
    """
    获取对话历史
    """
    app_service = get_app_service(request)
    messages = await app_service.message_repo.list_by_conversation(session_id, limit=limit)
    
    return {
        "session_id": session_id,
        "messages": [m.to_dict() for m in messages]
    }
