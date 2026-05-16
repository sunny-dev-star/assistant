"""
SQLAlchemy 租户仓储实现
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from ...domain.entities.tenant import Tenant
from ...domain.repositories.tenant_repository import ITenantRepository
from ...domain.value_objects.api_key import ApiKey
from ...domain.value_objects.quota import Quota


class SQLAlchemyTenantRepository(ITenantRepository):
    """SQLAlchemy 租户仓储实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """根据 ID 获取租户"""
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """根据 API Key 获取租户"""
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.api_key == api_key)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def create(self, tenant: Tenant) -> Tenant:
        """创建租户"""
        model = TenantModel(
            id=tenant.id,
            name=tenant.name,
            industry=tenant.industry,
            contact=tenant.contact,
            plan=tenant.plan,
            config=tenant.config,
            api_key=tenant.api_key.value,
            status=tenant.status,
            quota_limit=tenant.quota.limit,
            quota_used=tenant.quota.used
        )
        self.session.add(model)
        await self.session.flush()
        return tenant
    
    async def update(self, tenant: Tenant) -> Tenant:
        """更新租户"""
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
                updated_at=tenant.updated_at
            )
        )
        await self.session.flush()
        return tenant
    
    async def delete(self, tenant_id: str) -> bool:
        """删除租户"""
        result = await self.session.execute(
            delete(TenantModel).where(TenantModel.id == tenant_id)
        )
        await self.session.flush()
        return result.rowcount > 0
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """列出所有租户"""
        result = await self.session.execute(
            select(TenantModel).offset(skip).limit(limit)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]
    
    async def count(self) -> int:
        """统计租户数量"""
        result = await self.session.execute(
            select(func.count()).select_from(TenantModel)
        )
        return result.scalar()
    
    def _to_entity(self, model) -> Tenant:
        """转换为领域实体"""
        return Tenant(
            id=model.id,
            name=model.name,
            industry=model.industry,
            contact=model.contact,
            plan=model.plan,
            status=model.status,
            api_key=ApiKey(model.api_key),
            quota=Quota(limit=model.quota_limit, used=model.quota_used),
            config=model.config,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


# SQLAlchemy 模型
from sqlalchemy import Column, String, DateTime, Integer, JSON, func
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class TenantModel(Base):
    """租户数据库模型"""
    __tablename__ = "tenants"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    industry = Column(String(50))
    contact = Column(String(50))
    plan = Column(String(20), default="basic")
    config = Column(JSON, default=dict)
    api_key = Column(String(100), unique=True)
    status = Column(String(20), default="active")
    quota_used = Column(Integer, default=0)
    quota_limit = Column(Integer, default=100000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
