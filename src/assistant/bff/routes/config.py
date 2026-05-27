"""BFF config route - per-channel frontend config"""
from fastapi import APIRouter, Request, Path

router = APIRouter()


@router.get("/config")
async def get_config(tenant_id: str = Path(...), channel: str = "web", request: Request = None):
    """Return frontend config customized by channel"""
    cfg_repo = request.app.state.config_repo
    cfg = await cfg_repo.get(tenant_id)

    base = {
        "app_name": cfg.get("app_name", "智能助手"),
        "logo_url": cfg.get("logo_url"),
        "primary_color": cfg.get("primary_color", "#1890ff"),
        "welcome_message": cfg.get("welcome_message", "你好，有什么可以帮你？"),
    }

    if channel == "miniprogram":
        return {
            **base,
            "features": {**cfg.get("features", {}), "streaming": False},
            "auth_methods": {"wechat": True},
        }
    elif channel == "web":
        return {
            **base,
            "features": {**cfg.get("features", {}), "streaming": cfg.get("streaming_enabled", False)},
            "auth_methods": cfg.get("auth_methods", {}),
            "web_theme": cfg.get("web_theme", {}),
        }
    elif channel == "app":
        return {
            **base,
            "features": {
                **cfg.get("features", {}),
                "streaming": True,
                "push_notification": True,
                "biometric_auth": True,
            },
            "auth_methods": cfg.get("auth_methods", {}),
        }
    elif channel == "h5":
        return {
            **base,
            "features": {**cfg.get("features", {}), "streaming": False},
            "auth_methods": {"wechat": True, "phone": True},
        }
    return {**base, "features": cfg.get("features", {})}
