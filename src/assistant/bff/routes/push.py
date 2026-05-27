"""BFF push device registration"""
from fastapi import APIRouter, Request, Path
from pydantic import BaseModel

router = APIRouter()


class RegisterDeviceBody(BaseModel):
    device_token: str
    platform: str  # ios / android
    device_id: str


@router.post("/push/register")
async def register_push_device(body: RegisterDeviceBody, tenant_id: str = Path(...), request: Request = None):
    user_id = request.state.user_id
    push_repo = request.app.state.push_repo
    await push_repo.upsert({
        "user_id": user_id,
        "tenant_id": tenant_id,
        "platform": body.platform,
        "device_token": body.device_token,
    })
    return {"status": "registered"}
