"""
Tenant authentication middleware
Extracts tenant from Bearer token, injects into request.state.tenant
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ...infrastructure.config.settings import settings


PUBLIC_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc", "/", "/favicon.ico"})


class TenantAuthMiddleware(BaseHTTPMiddleware):
    """
    Authenticates requests via Bearer API Key.
    Injects Tenant entity into request.state.tenant.

    When AUTH_ENABLED=False (dev mode), uses the default tenant automatically.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/docs"):
            return await call_next(request)

        if not settings.AUTH_ENABLED:
            # Dev mode: auto-inject default tenant
            request.state.tenant = await self._get_default_tenant()
            return await call_next(request)

        # Production mode: require Bearer token
        api_key = self._extract_api_key(request)
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"code": 4010, "message": "Missing API Key. Use Authorization: Bearer <key>", "data": None}
            )

        tenant = await self._resolve_tenant(api_key)
        if not tenant:
            return JSONResponse(
                status_code=401,
                content={"code": 4011, "message": "Invalid API Key", "data": None}
            )

        if not tenant.is_active():
            return JSONResponse(
                status_code=401,
                content={"code": 4012, "message": f"Tenant is {tenant.status}", "data": None}
            )

        if tenant.quota.used >= tenant.quota.limit:
            return JSONResponse(
                status_code=429,
                content={"code": 4290, "message": "Quota exceeded", "data": None}
            )

        request.state.tenant = tenant
        return await call_next(request)

    def _extract_api_key(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        return None

    async def _resolve_tenant(self, api_key: str):
        """Look up tenant by API key from database"""
        from ..persistence.database import async_session_factory
        from ..persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository
        async with async_session_factory() as session:
            repo = SQLAlchemyTenantRepository(session)
            return await repo.get_by_api_key(api_key)

    async def _get_default_tenant(self):
        """Return a default tenant for dev mode"""
        from ...domain.entities.tenant import Tenant
        from ...domain.value_objects.api_key import ApiKey
        from ...domain.value_objects.quota import Quota
        return Tenant(
            id="tnt_default",
            name="Default Tenant (Dev)",
            plan="professional",
            status="active",
            api_key=ApiKey("ak_dev_test_key_12345"),
            quota=Quota(limit=1000000, used=0),
            config={
                "window_size": 10,
                "default_model": "deepseek/deepseek-chat",
                "enabled_skills": ["weather_query", "express_query"],
            }
        )
