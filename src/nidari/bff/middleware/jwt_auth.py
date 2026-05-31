"""
JWT authentication middleware for BFF layer.
Supports both Authorization header and httpOnly cookie.
"""
import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ...infrastructure.config.settings import settings


# Paths that skip JWT auth
PUBLIC_PATHS = {
    "/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico",
}

# Path prefixes that skip JWT auth
PUBLIC_PREFIXES = (
    "/bff/",
)

# Auth sub-paths that are public (login, register, etc.)
AUTH_PUBLIC_PATHS = {
    "auth/wechat",
    "auth/phone",
    "auth/email/register",
    "auth/email",
    "auth/sso",
    "auth/refresh",
    "auth/logout",
    "config",
}


class BFFJWTAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT auth for BFF routes.
    Extracts user_id and tenant_id from JWT token.
    Supports: Authorization: Bearer <token> OR httpOnly cookie.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip non-BFF paths
        if path in PUBLIC_PATHS or not path.startswith("/bff/"):
            return await call_next(request)

        # Check if this is a public BFF endpoint
        if self._is_public_bff_path(path, request.method):
            return await call_next(request)

        # Extract JWT
        token = self._extract_token(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"code": 4010, "message": "Missing authentication token", "data": None}
            )

        # Verify JWT
        try:
            payload = self._verify_token(token, request)
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"code": 4011, "message": "Token expired", "data": None}
            )
        except jwt.InvalidTokenError as e:
            return JSONResponse(
                status_code=401,
                content={"code": 4012, "message": f"Invalid token: {str(e)}", "data": None}
            )

        # Inject into request.state
        request.state.user_id = payload.get("user_id")
        request.state.tenant_id = payload.get("tenant_id")

        return await call_next(request)

    def _extract_token(self, request: Request) -> str | None:
        # Priority 1: Authorization header (App / Mini-program / API)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        # Priority 2: httpOnly cookie (Web browser)
        return request.cookies.get("access_token")

    def _verify_token(self, token: str, request: Request) -> dict:
        # Get tenant_id from URL path to find the right secret
        # /bff/{tenant_id}/...
        parts = request.url.path.split("/")
        tenant_id = parts[2] if len(parts) > 2 else None

        # For now use shared secret; in production per-tenant secret
        secret = settings.BFF_JWT_SECRET or settings.SECRET_KEY
        return jwt.decode(token, secret, algorithms=["HS256"])

    def _is_public_bff_path(self, path: str, method: str) -> bool:
        """Check if a BFF path is public (no auth required)."""
        # /bff/{tenant_id}/config is public GET
        parts = path.rstrip("/").split("/")
        if len(parts) < 4:
            return True

        action = "/".join(parts[3:])  # e.g., "auth/wechat", "config"

        if action == "config" and method == "GET":
            return True
        for public in AUTH_PUBLIC_PATHS:
            if action.startswith(public):
                return True
        return False
