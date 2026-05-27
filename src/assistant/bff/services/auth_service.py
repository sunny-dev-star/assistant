"""
Unified authentication service for all channels.
"""
import bcrypt
import jwt
import uuid
import time
import hashlib
from typing import Optional


class AuthService:
    """
    统一认证服务，处理所有登录方式，颁发统一格式的 JWT。
    """

    ACCESS_TOKEN_TTL = 3 * 3600       # 3 hours
    REFRESH_TOKEN_TTL = 30 * 24 * 3600  # 30 days

    def __init__(self, user_repo, identity_repo, refresh_repo, config_repo):
        self.user_repo = user_repo
        self.identity_repo = identity_repo
        self.refresh_repo = refresh_repo
        self.config_repo = config_repo

    # ── WeChat Login (Mini-program + H5) ──────────────────

    async def login_wechat(self, tenant_id: str, code: str, channel: str) -> dict:
        cfg = await self.config_repo.get(tenant_id)
        openid, unionid = await self._exchange_wechat_code(
            code, cfg.get("wechat_appid", ""), cfg.get("wechat_secret", ""), channel
        )
        provider = f"wechat_{channel}"
        user, is_new = await self._get_or_create_by_identity(
            tenant_id, provider, openid,
            extra={"unionid": unionid}
        )
        return await self._issue_tokens(tenant_id, user, channel, is_new)

    # ── Phone + SMS Code ──────────────────────────────────

    async def send_sms_code(self, tenant_id: str, phone: str):
        # TODO: integrate real SMS provider
        # For now, log the code
        import random
        code = str(random.randint(100000, 999999))
        # In production: store in Redis with TTL 300s
        # await self.redis.setex(f"sms:{tenant_id}:{phone}", 300, code)
        print(f"[SMS] code for {phone}: {code}")  # dev only
        return code

    async def login_phone(self, tenant_id: str, phone: str, code: str, channel: str) -> dict:
        # TODO: validate against Redis stored code
        # For dev: accept any 6-digit code
        if len(code) != 6 or not code.isdigit():
            raise ValueError("验证码格式错误")

        user, is_new = await self.user_repo.get_or_create_by_phone(tenant_id, phone)
        return await self._issue_tokens(tenant_id, user, channel, is_new)

    # ── Email + Password ──────────────────────────────────

    async def login_email(self, tenant_id: str, email: str, password: str, channel: str) -> dict:
        user = await self.user_repo.get_by_email(tenant_id, email)
        if not user:
            raise ValueError("邮箱或密码错误")
        if not user.get("password_hash"):
            raise ValueError("该邮箱未设置密码，请使用其他方式登录")
        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            raise ValueError("邮箱或密码错误")
        return await self._issue_tokens(tenant_id, user, channel)

    async def register_email(self, tenant_id: str, email: str, password: str, display_name: str = "") -> dict:
        existing = await self.user_repo.get_by_email(tenant_id, email)
        if existing:
            raise ValueError("邮箱已注册")
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = await self.user_repo.create({
            "id": f"usr_{uuid.uuid4().hex[:10]}",
            "tenant_id": tenant_id,
            "email": email,
            "password_hash": pw_hash,
            "display_name": display_name or email.split("@")[0],
        })
        return await self._issue_tokens(tenant_id, user, "web", is_new=True)

    # ── Enterprise SSO (Feishu / DingTalk) ───────────────

    async def login_sso(self, tenant_id: str, provider: str, code: str, channel: str) -> dict:
        # TODO: implement real SSO code exchange
        user_info = await self._exchange_sso_code(provider, code, tenant_id)
        user, is_new = await self._get_or_create_by_identity(
            tenant_id, provider,
            provider_uid=user_info["uid"],
            extra=user_info,
            display_name=user_info.get("name"),
            avatar_url=user_info.get("avatar"),
        )
        return await self._issue_tokens(tenant_id, user, channel, is_new)

    # ── Token Refresh ─────────────────────────────────────

    async def refresh_access_token(self, tenant_id: str, refresh_token: str) -> dict:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        record = await self.refresh_repo.get(token_hash)

        if not record or record["revoked"]:
            raise ValueError("Refresh Token 无效")
        if record["expires_at"] < time.time():
            raise ValueError("Refresh Token 已过期，请重新登录")
        if record["tenant_id"] != tenant_id:
            raise ValueError("Token 与租户不匹配")

        user = await self.user_repo.get_by_id(record["user_id"])
        if not user:
            raise ValueError("用户不存在")
        cfg = await self.config_repo.get(tenant_id)

        new_access = self._sign_access_token(tenant_id, user["id"], cfg)

        # Rotation: issue new refresh, revoke old
        await self.refresh_repo.revoke(token_hash)
        new_refresh = await self._issue_refresh_token(
            tenant_id, user["id"], record["channel"], record.get("device_id")
        )
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": self.ACCESS_TOKEN_TTL,
        }

    # ── Logout ────────────────────────────────────────────

    async def logout(self, tenant_id: str, refresh_token: str):
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        await self.refresh_repo.revoke(token_hash)

    async def logout_all_devices(self, tenant_id: str, user_id: str):
        await self.refresh_repo.revoke_all_for_user(user_id, tenant_id)

    # ── Private methods ───────────────────────────────────

    async def _issue_tokens(self, tenant_id: str, user: dict, channel: str,
                            is_new: bool = False, device_id: str = None) -> dict:
        cfg = await self.config_repo.get(tenant_id)
        access_token = self._sign_access_token(tenant_id, user["id"], cfg)
        refresh_token = await self._issue_refresh_token(
            tenant_id, user["id"], channel, device_id
        )
        await self.user_repo.update_last_login(user["id"], channel)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.ACCESS_TOKEN_TTL,
            "user_id": user["id"],
            "display_name": user.get("display_name"),
            "avatar_url": user.get("avatar_url"),
            "is_new_user": is_new,
        }

    def _sign_access_token(self, tenant_id: str, user_id: str, cfg: dict) -> str:
        secret = cfg.get("jwt_secret", "change-me-in-production")
        return jwt.encode({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.ACCESS_TOKEN_TTL,
        }, secret, algorithm="HS256")

    async def _issue_refresh_token(self, tenant_id: str, user_id: str,
                                    channel: str, device_id: str = None) -> str:
        raw = f"{uuid.uuid4()}{time.time()}"
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        await self.refresh_repo.create({
            "id": token_hash,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "channel": channel,
            "device_id": device_id,
            "expires_at": time.time() + self.REFRESH_TOKEN_TTL,
        })
        return raw

    async def _get_or_create_by_identity(self, tenant_id: str, provider: str,
                                          provider_uid: str, extra: dict = None,
                                          display_name: str = None,
                                          avatar_url: str = None) -> tuple[dict, bool]:
        identity = await self.identity_repo.get(tenant_id, provider, provider_uid)
        if identity:
            user = await self.user_repo.get_by_id(identity["user_id"])
            return user, False
        user = await self.user_repo.create({
            "id": f"usr_{uuid.uuid4().hex[:10]}",
            "tenant_id": tenant_id,
            "display_name": display_name or "用户",
            "avatar_url": avatar_url,
        })
        await self.identity_repo.create({
            "user_id": user["id"],
            "tenant_id": tenant_id,
            "provider": provider,
            "provider_uid": provider_uid,
            "extra": extra or {},
        })
        return user, True

    # ── Stub: WeChat code exchange ────────────────────────

    async def _exchange_wechat_code(self, code: str, appid: str, secret: str, channel: str):
        # TODO: real WeChat API call
        # For dev: use code as openid
        import hashlib
        openid = hashlib.md5(code.encode()).hexdigest()[:28]
        return openid, None

    async def _exchange_sso_code(self, provider: str, code: str, tenant_id: str):
        # TODO: real SSO provider exchange
        import hashlib
        uid = hashlib.md5(f"{provider}:{code}".encode()).hexdigest()[:28]
        return {"uid": uid, "name": f"{provider}用户", "avatar": None}
