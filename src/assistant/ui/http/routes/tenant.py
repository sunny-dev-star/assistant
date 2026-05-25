"""
租户管理路由 — 含角色自动初始化
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter()


class CreateTenantRequest(BaseModel):
    """创建租户请求"""
    name: str
    industry: Optional[str] = None
    contact: Optional[str] = None
    plan: str = "basic"
    config: Optional[Dict[str, Any]] = None


class TenantResponse(BaseModel):
    """租户响应"""
    tenant_id: str
    name: str
    industry: Optional[str]
    plan: str
    status: str
    api_key: str
    created_at: str


@router.post("/tenants")
async def create_tenant(req: CreateTenantRequest, request: Request):
    """
    创建租户 — 同时自动初始化 admin + default 两个角色
    """
    from ....infrastructure.persistence.database import async_session_factory
    from ....infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository
    from ....infrastructure.persistence.repositories.role_repo import RoleRepository
    from ....domain.services.tenant_service import TenantService

    async with async_session_factory() as session:
        tenant_repo = SQLAlchemyTenantRepository(session)
        role_repo = RoleRepository(session)
        service = TenantService(tenant_repo, role_repo)

        result = await service.create_tenant(
            name=req.name,
            industry=req.industry,
            plan=req.plan,
        )
        await session.commit()

        tenant = result["tenant"]
        return {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "industry": tenant.industry,
            "plan": tenant.plan,
            "status": tenant.status,
            "api_key": result["api_key"],
            "admin_role": result.get("admin_role"),
            "default_role": result.get("default_role"),
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        }


@router.get("/tenants")
async def list_tenants(skip: int = 0, limit: int = 100):
    """获取租户列表"""
    from ....infrastructure.persistence.database import async_session_factory
    from ....infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository

    async with async_session_factory() as session:
        repo = SQLAlchemyTenantRepository(session)
        tenants = await repo.list_all(skip=skip, limit=limit)
        return [{
            "tenant_id": t.id,
            "name": t.name,
            "industry": t.industry,
            "plan": t.plan,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in tenants]


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    """获取租户详情"""
    from ....infrastructure.persistence.database import async_session_factory
    from ....infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository

    async with async_session_factory() as session:
        repo = SQLAlchemyTenantRepository(session)
        tenant = await repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return tenant.to_dict()


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str):
    """删除租户"""
    from ....infrastructure.persistence.database import async_session_factory
    from ....infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository

    async with async_session_factory() as session:
        repo = SQLAlchemyTenantRepository(session)
        success = await repo.delete(tenant_id)
        await session.commit()
        if not success:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return {"status": "deleted", "tenant_id": tenant_id}
