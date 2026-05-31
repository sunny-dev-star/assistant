"""Refresh token repository"""
from sqlalchemy import select, update
from ..models.bff_models import RefreshTokenModel


class RefreshTokenRepository:
    def __init__(self, session):
        self.session = session

    async def get(self, token_hash: str) -> dict | None:
        result = await self.session.get(RefreshTokenModel, token_hash)
        if not result:
            return None
        return {
            "id": result.id,
            "user_id": result.user_id,
            "tenant_id": result.tenant_id,
            "channel": result.channel,
            "device_id": result.device_id,
            "issued_at": result.issued_at,
            "expires_at": result.expires_at.timestamp() if result.expires_at else 0,
            "revoked": result.revoked,
        }

    async def create(self, data: dict) -> dict:
        from datetime import datetime
        if isinstance(data.get("expires_at"), (int, float)):
            data["expires_at"] = datetime.utcfromtimestamp(data["expires_at"])
        token = RefreshTokenModel(**data)
        self.session.add(token)
        await self.session.flush()
        return {"id": token.id}

    async def revoke(self, token_hash: str):
        token = await self.session.get(RefreshTokenModel, token_hash)
        if token:
            token.revoked = True
            from datetime import datetime
            token.revoked_at = datetime.utcnow()
            await self.session.flush()

    async def revoke_all_for_user(self, user_id: str, tenant_id: str):
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.tenant_id == tenant_id,
                RefreshTokenModel.revoked == False,
            )
            .values(revoked=True)
        )
        await self.session.execute(stmt)
        await self.session.flush()
