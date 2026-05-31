"""Auth identity repository"""
from sqlalchemy import select
from ..models.bff_models import AuthIdentityModel


class AuthIdentityRepository:
    def __init__(self, session):
        self.session = session

    async def get(self, tenant_id: str, provider: str, provider_uid: str) -> dict | None:
        stmt = select(AuthIdentityModel).where(
            AuthIdentityModel.tenant_id == tenant_id,
            AuthIdentityModel.provider == provider,
            AuthIdentityModel.provider_uid == provider_uid,
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        if not result:
            return None
        return {
            "id": result.id,
            "user_id": result.user_id,
            "tenant_id": result.tenant_id,
            "provider": result.provider,
            "provider_uid": result.provider_uid,
            "extra": result.extra,
        }

    async def create(self, data: dict) -> dict:
        identity = AuthIdentityModel(**data)
        self.session.add(identity)
        await self.session.flush()
        return {
            "id": identity.id,
            "user_id": identity.user_id,
            "tenant_id": identity.tenant_id,
            "provider": identity.provider,
            "provider_uid": identity.provider_uid,
            "extra": identity.extra,
        }
