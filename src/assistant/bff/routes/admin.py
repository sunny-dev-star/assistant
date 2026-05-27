"""BFF admin routes"""
from fastapi import APIRouter, Request, Path
from pydantic import BaseModel

router = APIRouter()


class ConfigUpdateBody(BaseModel):
    app_name: str | None = None
    primary_color: str | None = None
    welcome_message: str | None = None
    auth_methods: dict | None = None
    streaming_enabled: bool | None = None
    web_theme: dict | None = None


@router.get("/admin/config")
async def get_admin_config(tenant_id: str = Path(...), request: Request = None):
    cfg_repo = request.app.state.config_repo
    return await cfg_repo.get(tenant_id)


@router.put("/admin/config")
async def update_admin_config(body: ConfigUpdateBody, tenant_id: str = Path(...), request: Request = None):
    cfg_repo = request.app.state.config_repo
    data = {k: v for k, v in body.dict().items() if v is not None}
    return await cfg_repo.upsert(tenant_id, data)


@router.get("/admin/users")
async def list_users(tenant_id: str = Path(...), request: Request = None):
    # TODO: implement with pagination
    return {"users": [], "total": 0}
