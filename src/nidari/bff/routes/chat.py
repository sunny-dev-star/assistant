"""BFF chat routes - regular + SSE streaming"""
import json
import httpx
from fastapi import APIRouter, Request, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class BFFChatRequest(BaseModel):
    content: str
    session_id: str | None = None
    channel: str = "web"


@router.post("/chat")
async def bff_chat(body: BFFChatRequest, tenant_id: str = Path(...), request: Request = None):
    """Regular chat - proxies to core API"""
    user_id = request.state.user_id
    core_url = request.app.state.core_api_url

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{core_url}/v1/chat",
            headers={
                "Authorization": f"Bearer {request.app.state.internal_token}",
                "X-User-Id": user_id,
                "X-Tenant-Id": tenant_id,
            },
            json={
                "content": body.content,
                "user_id": user_id,
                "session_id": body.session_id,
                "channel": body.channel,
            },
            timeout=120.0,
        )
        return resp.json()


@router.post("/chat/stream")
async def bff_chat_stream(body: BFFChatRequest, tenant_id: str = Path(...), request: Request = None):
    """SSE streaming chat - Web/App only"""
    user_id = request.state.user_id
    core_url = request.app.state.core_api_url

    async def stream_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{core_url}/v1/chat",
                headers={
                    "Authorization": f"Bearer {request.app.state.internal_token}",
                    "X-User-Id": user_id,
                    "X-Tenant-Id": tenant_id,
                    "Accept": "text/event-stream",
                },
                json={
                    "content": body.content,
                    "user_id": user_id,
                    "session_id": body.session_id,
                    "channel": body.channel,
                    "stream": True,
                },
                timeout=120.0,
            ) as resp:
                async for chunk in resp.aiter_text():
                    if chunk:
                        yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
