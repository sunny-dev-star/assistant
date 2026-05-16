"""
对话路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ....application.dtos.chat_dto import ChatRequestDTO
from ....application.use_cases.chat_use_case import ChatUseCase

router = APIRouter()


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    channel: str = "web"
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    message_id: str
    reply: str
    tokens_used: int = 0


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_req: ChatRequest
):
    """
    发起对话
    """
    # 获取租户 ID（从请求头或路径）
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    
    # 构建 DTO
    dto = ChatRequestDTO(
        message=chat_req.message,
        session_id=chat_req.session_id,
        user_id=chat_req.user_id,
        channel=chat_req.channel,
        metadata=chat_req.metadata
    )
    
    # 执行用例
    # TODO: 注入 use case
    # result = await chat_use_case.execute(tenant_id, dto)
    
    # 临时返回
    return ChatResponse(
        session_id=chat_req.session_id or "new_session",
        message_id="msg_123",
        reply=f"收到消息：{chat_req.message}",
        tokens_used=0
    )


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    获取对话历史
    """
    return {
        "session_id": session_id,
        "messages": []
    }
