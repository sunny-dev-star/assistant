"""BFF upload route"""
import httpx
from fastapi import APIRouter, Request, Path, UploadFile, File

router = APIRouter()


@router.post("/upload")
async def upload_file(tenant_id: str = Path(...), file: UploadFile = File(...), request: Request = None):
    """Proxy upload to core API"""
    user_id = request.state.user_id
    core_url = request.app.state.core_api_url

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{core_url}/v1/upload",
            headers={
                "Authorization": f"Bearer {request.app.state.internal_token}",
                "X-User-Id": user_id,
                "X-Tenant-Id": tenant_id,
            },
            files={"file": (file.filename, await file.read(), file.content_type)},
            timeout=60.0,
        )
        return resp.json()
