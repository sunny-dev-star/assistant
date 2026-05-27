"""BFF history routes"""
import httpx
from fastapi import APIRouter, Request, Path

router = APIRouter()


@router.get("/history/sessions")
async def list_sessions(tenant_id: str = Path(...), request: Request = None):
    user_id = request.state.user_id
    core_url = request.app.state.core_api_url
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{core_url}/v1/chat/sessions",
            headers={
                "Authorization": f"Bearer {request.app.state.internal_token}",
                "X-User-Id": user_id,
                "X-Tenant-Id": tenant_id,
            },
        )
        return resp.json()


@router.get("/history/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, tenant_id: str = Path(...), request: Request = None):
    user_id = request.state.user_id
    core_url = request.app.state.core_api_url
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{core_url}/v1/chat/sessions/{session_id}/messages",
            headers={
                "Authorization": f"Bearer {request.app.state.internal_token}",
                "X-User-Id": user_id,
                "X-Tenant-Id": tenant_id,
            },
        )
        return resp.json()


@router.delete("/history/sessions/{session_id}")
async def delete_session(session_id: str, tenant_id: str = Path(...), request: Request = None):
    user_id = request.state.user_id
    core_url = request.app.state.core_api_url
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{core_url}/v1/chat/sessions/{session_id}",
            headers={
                "Authorization": f"Bearer {request.app.state.internal_token}",
                "X-User-Id": user_id,
                "X-Tenant-Id": tenant_id,
            },
        )
        return resp.json()
