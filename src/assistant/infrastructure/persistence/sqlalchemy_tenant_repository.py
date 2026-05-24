"""
SQLAlchemy tenant repository implementation
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from ...domain.entities.tenant import Tenant
from ...domain.repositories.tenant_repository import ITenantRepository
from ...domain.value_objects.api_key import ApiKey
from ...domain.value_objects.quota import Quota
from .models import TenantModel


class SQLAlchemyTenantRepository(ITenantRepository):
    """SQLAlchemy tenant repo"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_api_key(self, api_key: str) -> Optional[Tenant]:
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.api_key == api_key)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, tenant: Tenant) -> Tenant:
        model = self._to_model(tenant)
        self.session.add(model)
        await self.session.flush()
        return tenant

    async def update(self, tenant: Tenant) -> Tenant:
        await self.session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                name=tenant.name,
                industry=tenant.industry,
                contact=tenant.contact,
                plan=tenant.plan,
                config=tenant.config,
                status=tenant.status,
                quota_limit=tenant.quota.limit,
                quota_used=tenant.quota.used,
                window_size=tenant.config.get("window_size", 10),
                default_model=tenant.config.get("default_model", "deepseek/deepseek-chat"),
                updated_at=tenant.updated_at,
            )
        )
        await self.session.flush()
        return tenant

    async def delete(self, tenant_id: str) -> bool:
        result = await self.session.execute(
            delete(TenantModel).where(TenantModel.id == tenant_id)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        result = await self.session.execute(
            select(TenantModel).offset(skip).limit(limit)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(TenantModel)
        )
        return result.scalar()

    async def increment_quota(self, tenant_id: str, tokens: int):
        await self.session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant_id)
            .values(quota_used=TenantModel.quota_used + tokens)
        )
        await self.session.flush()

    def _to_entity(self, model: TenantModel) -> Tenant:
        config = dict(model.config or {})
        config["window_size"] = model.window_size
        config["default_model"] = model.default_model
        config["enabled_skills"] = model.enabled_skills or []
        return Tenant(
            id=model.id,
            name=model.name,
            industry=model.industry,
            contact=model.contact,
            plan=model.plan,
            status=model.status,
            api_key=ApiKey(model.api_key),
            quota=Quota(limit=model.quota_limit, used=model.quota_used),
            config=config,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Tenant) -> TenantModel:
        return TenantModel(
            id=entity.id,
            name=entity.name,
            industry=entity.industry,
            contact=entity.contact,
            plan=entity.plan,
            status=entity.status,
            api_key=entity.api_key.value,
            quota_limit=entity.quota.limit,
            quota_used=entity.quota.used,
            config=entity.config,
            window_size=entity.config.get("window_size", 10),
            default_model=entity.config.get("default_model", "deepseek/deepseek-chat"),
            enabled_skills=entity.config.get("enabled_skills", []),
        )
