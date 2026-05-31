"""User repository for BFF platform_users"""
from sqlalchemy import select
from ...infrastructure.persistence.database import async_session_factory
from ..models.bff_models import PlatformUserModel


class BFFUserRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_id(self, user_id: str) -> dict | None:
        result = await self.session.get(PlatformUserModel, user_id)
        return self._to_dict(result) if result else None

    async def get_by_phone(self, tenant_id: str, phone: str) -> dict | None:
        stmt = select(PlatformUserModel).where(
            PlatformUserModel.tenant_id == tenant_id,
            PlatformUserModel.phone == phone,
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_dict(result) if result else None

    async def get_by_email(self, tenant_id: str, email: str) -> dict | None:
        stmt = select(PlatformUserModel).where(
            PlatformUserModel.tenant_id == tenant_id,
            PlatformUserModel.email == email,
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_dict(result) if result else None

    async def get_or_create_by_phone(self, tenant_id: str, phone: str) -> tuple[dict, bool]:
        existing = await self.get_by_phone(tenant_id, phone)
        if existing:
            return existing, False
        import uuid
        user = PlatformUserModel(
            id=f"usr_{uuid.uuid4().hex[:10]}",
            tenant_id=tenant_id,
            phone=phone,
            display_name=f"用户{phone[-4:]}",
        )
        self.session.add(user)
        await self.session.flush()
        return self._to_dict(user), True

    async def create(self, data: dict) -> dict:
        user = PlatformUserModel(**data)
        self.session.add(user)
        await self.session.flush()
        return self._to_dict(user)

    async def update_last_login(self, user_id: str, channel: str):
        from datetime import datetime
        user = await self.session.get(PlatformUserModel, user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            user.last_login_channel = channel
            await self.session.flush()

    def _to_dict(self, obj) -> dict:
        if not obj:
            return None
        return {
            "id": obj.id,
            "tenant_id": obj.tenant_id,
            "display_name": obj.display_name,
            "avatar_url": obj.avatar_url,
            "phone": obj.phone,
            "email": obj.email,
            "password_hash": obj.password_hash,
            "is_active": obj.is_active,
            "last_login_at": obj.last_login_at.isoformat() if obj.last_login_at else None,
            "last_login_channel": obj.last_login_channel,
        }
