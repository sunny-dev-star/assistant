"""
BFF (Backend For Frontend) - Unified entry point for all frontend channels.
Runs as a separate process on port 8001.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Path, Response
from fastapi.middleware.cors import CORSMiddleware

from ..infrastructure.config.settings import settings
from ..infrastructure.persistence.database import async_session_factory, init_db
from .middleware.jwt_auth import BFFJWTAuthMiddleware
from .repositories.user_repo import BFFUserRepository
from .repositories.identity_repo import AuthIdentityRepository
from .repositories.refresh_token_repo import RefreshTokenRepository
from .repositories.push_device_repo import PushDeviceRepository
from .repositories.config_repo import TenantFrontendConfigRepository
from .services.auth_service import AuthService
from .routes.config import router as config_router
from .routes.chat import router as chat_router
from .routes.upload import router as upload_router
from .routes.history import router as history_router
from .routes.push import router as push_router
from .routes.profile import router as profile_router
from .routes.admin import router as admin_router
from .routes.push import RegisterDeviceBody


@asynccontextmanager
async def lifespan(app: FastAPI):
    """BFF lifecycle: init DB, repositories, services."""
    # Ensure BFF tables exist
    from .models.bff_models import (  # noqa
        PlatformUserModel, AuthIdentityModel, RefreshTokenModel,
        PushDeviceModel, TenantFrontendConfigModel,
    )
    await init_db()
    print("[BFF] Database tables ensured.")

    # Store shared objects in app.state
    app.state.core_api_url = settings.CORE_API_URL if hasattr(settings, 'CORE_API_URL') else "http://localhost:8000"
    app.state.internal_token = getattr(settings, 'INTERNAL_TOKEN', 'dev-internal-token')

    print(f"[BFF] Core API: {app.state.core_api_url}")
    print("=== BFF API v1.0 ready ===")
    yield


app = FastAPI(
    title="BFF API",
    description="Backend For Frontend - Unified multi-channel entry",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(BFFJWTAuthMiddleware)

# ── Config (public, no auth) ──
app.include_router(config_router, prefix="/bff/{tenant_id}", tags=["Config"])

# ── Auth routes (public) ──
# We define auth routes inline here because they need DI access to AuthService

from .routes.auth import (
    WechatLoginBody, PhoneSendCodeBody, PhoneLoginBody,
    EmailRegisterBody, EmailLoginBody, SSOLoginBody,
    RefreshBody, LogoutBody,
)


def _get_auth_service(request: Request) -> AuthService:
    """Create AuthService with fresh DB session"""
    session = async_session_factory()
    user_repo = BFFUserRepository(session)
    identity_repo = AuthIdentityRepository(session)
    refresh_repo = RefreshTokenRepository(session)
    config_repo = TenantFrontendConfigRepository(session)
    return AuthService(user_repo, identity_repo, refresh_repo, config_repo), session


@app.post("/bff/{tenant_id}/auth/wechat")
async def login_wechat(body: WechatLoginBody, tenant_id: str = Path(...)):
    svc, session = _get_auth_service()
    try:
        result = await svc.login_wechat(tenant_id, body.code, body.channel)
        await session.commit()
        return result
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


@app.post("/bff/{tenant_id}/auth/phone/send-code")
async def send_sms_code(body: PhoneSendCodeBody, tenant_id: str = Path(...)):
    svc, session = _get_auth_service()
    try:
        code = await svc.send_sms_code(tenant_id, body.phone)
        await session.commit()
        return {"message": "验证码已发送", "code": code}  # dev: return code
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


@app.post("/bff/{tenant_id}/auth/phone")
async def login_phone(body: PhoneLoginBody, tenant_id: str = Path(...)):
    svc, session = _get_auth_service()
    try:
        result = await svc.login_phone(tenant_id, body.phone, body.code, body.channel)
        await session.commit()
        return result
    except ValueError as e:
        await session.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@app.post("/bff/{tenant_id}/auth/email/register")
async def register_email(body: EmailRegisterBody, tenant_id: str = Path(...)):
    svc, session = _get_auth_service()
    try:
        result = await svc.register_email(tenant_id, body.email, body.password, body.display_name)
        await session.commit()
        return result
    except ValueError as e:
        await session.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@app.post("/bff/{tenant_id}/auth/email")
async def login_email(body: EmailLoginBody, tenant_id: str = Path(...), response: Response = None):
    svc, session = _get_auth_service()
    try:
        result = await svc.login_email(tenant_id, body.email, body.password, body.channel)
        await session.commit()

        # Web channel: set httpOnly cookies instead of returning tokens in body
        if body.channel == "web":
            response.set_cookie(
                key="access_token",
                value=result["access_token"],
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=result["expires_in"],
            )
            response.set_cookie(
                key="refresh_token",
                value=result["refresh_token"],
                httponly=True,
                secure=True,
                samesite="strict",
                path=f"/bff/{tenant_id}/auth/refresh",
                max_age=30 * 24 * 3600,
            )
            # Don't return tokens in body for web
            result.pop("access_token", None)
            result.pop("refresh_token", None)

        return result
    except ValueError as e:
        await session.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@app.post("/bff/{tenant_id}/auth/sso")
async def login_sso(body: SSOLoginBody, tenant_id: str = Path(...)):
    svc, session = _get_auth_service()
    try:
        result = await svc.login_sso(tenant_id, body.provider, body.code, body.channel)
        await session.commit()
        return result
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


@app.post("/bff/{tenant_id}/auth/refresh")
async def refresh_token(body: RefreshBody, tenant_id: str = Path(...)):
    svc, session = _get_auth_service()
    try:
        result = await svc.refresh_access_token(tenant_id, body.refresh_token)
        await session.commit()
        return result
    except ValueError as e:
        await session.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@app.post("/bff/{tenant_id}/auth/logout")
async def logout(body: LogoutBody, tenant_id: str = Path(...)):
    svc, session = _get_auth_service()
    try:
        await svc.logout(tenant_id, body.refresh_token)
        await session.commit()
        return {"message": "已退出"}
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ── Authenticated routes ──
# These need DI too - override the route handlers

@app.post("/bff/{tenant_id}/chat")
async def bff_chat(request: Request, tenant_id: str = Path(...)):
    """Proxy chat to core API"""
    from .routes.chat import BFFChatRequest
    body = await request.json()
    chat_req = BFFChatRequest(**body)
    import httpx
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
                "content": chat_req.content,
                "user_id": user_id,
                "session_id": chat_req.session_id,
                "channel": chat_req.channel,
            },
            timeout=120.0,
        )
        return resp.json()


@app.post("/bff/{tenant_id}/chat/stream")
async def bff_chat_stream(request: Request, tenant_id: str = Path(...)):
    """SSE streaming chat"""
    from .routes.chat import BFFChatRequest
    from fastapi.responses import StreamingResponse
    body = await request.json()
    chat_req = BFFChatRequest(**body)
    import httpx
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
                    "content": chat_req.content,
                    "user_id": user_id,
                    "session_id": chat_req.session_id,
                    "channel": chat_req.channel,
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/bff/{tenant_id}/profile")
async def get_profile(request: Request, tenant_id: str = Path(...)):
    session = async_session_factory()
    try:
        user_repo = BFFUserRepository(session)
        user = await user_repo.get_by_id(request.state.user_id)
        await session.commit()
        if not user:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "user_id": user["id"],
            "display_name": user.get("display_name"),
            "avatar_url": user.get("avatar_url"),
            "phone": user.get("phone"),
            "email": user.get("email"),
            "last_login_channel": user.get("last_login_channel"),
        }
    finally:
        await session.close()


@app.post("/bff/{tenant_id}/push/register")
async def register_push(request: Request, body: RegisterDeviceBody, tenant_id: str = Path(...)):
    session = async_session_factory()
    try:
        push_repo = PushDeviceRepository(session)
        await push_repo.upsert({
            "user_id": request.state.user_id,
            "tenant_id": tenant_id,
            "platform": body.platform,
            "device_token": body.device_token,
        })
        await session.commit()
        return {"status": "registered"}
    finally:
        await session.close()


@app.get("/bff/{tenant_id}/history/sessions")
async def list_sessions(request: Request, tenant_id: str = Path(...)):
    import httpx
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


@app.get("/bff/{tenant_id}/history/sessions/{session_id}/messages")
async def get_session_messages(request: Request, session_id: str, tenant_id: str = Path(...)):
    import httpx
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


@app.delete("/bff/{tenant_id}/history/sessions/{session_id}")
async def delete_session(request: Request, session_id: str, tenant_id: str = Path(...)):
    import httpx
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


# Admin routes
@app.get("/bff/{tenant_id}/admin/config")
async def get_admin_config(request: Request, tenant_id: str = Path(...)):
    session = async_session_factory()
    try:
        cfg_repo = TenantFrontendConfigRepository(session)
        result = await cfg_repo.get(tenant_id)
        await session.commit()
        return result
    finally:
        await session.close()


@app.put("/bff/{tenant_id}/admin/config")
async def update_admin_config(request: Request, tenant_id: str = Path(...)):
    from .routes.admin import ConfigUpdateBody
    body = await request.json()
    update = ConfigUpdateBody(**body)
    session = async_session_factory()
    try:
        cfg_repo = TenantFrontendConfigRepository(session)
        data = {k: v for k, v in update.dict().items() if v is not None}
        result = await cfg_repo.upsert(tenant_id, data)
        await session.commit()
        return result
    finally:
        await session.close()


@app.get("/bff/{tenant_id}/admin/users")
async def list_users(request: Request, tenant_id: str = Path(...)):
    # TODO: implement with pagination
    return {"users": [], "total": 0}


@app.get("/")
async def root():
    return {"service": "BFF API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("assistant.bff.main:app", host="0.0.0.0", port=8001, reload=True)
