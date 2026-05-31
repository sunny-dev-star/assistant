"""
租户管理路由 — 含角色自动初始化 + 配置管理
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


class UpdateTenantConfigRequest(BaseModel):
    """更新租户配置请求"""
    # LLM 文本模型配置
    default_model: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_max_tokens: Optional[int] = None
    # 视觉模型配置（图片理解）
    vision_model: Optional[str] = None          # e.g. "gpt-4o", "qwen-vl-max"
    vision_api_base: Optional[str] = None
    vision_api_key: Optional[str] = None
    # 语音转文字配置
    stt_provider: Optional[str] = None           # "whisper", "aliyun", "tencent"
    stt_model: Optional[str] = None              # "whisper-1"
    stt_api_base: Optional[str] = None
    stt_api_key: Optional[str] = None
    # 技能配置
    enabled_skills: Optional[List[str]] = None
    # 通用配置
    window_size: Optional[int] = None


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
            config=req.config,
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
            "config": tenant.config,
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
            "config": t.config,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in tenants]


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    """获取租户详情（含完整配置）"""
    from ....infrastructure.persistence.database import async_session_factory
    from ....infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository

    async with async_session_factory() as session:
        repo = SQLAlchemyTenantRepository(session)
        tenant = await repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        d = tenant.to_dict()
        # 脱敏：不返回 llm_api_key 明文
        if d.get("config", {}).get("llm_api_key"):
            key = d["config"]["llm_api_key"]
            d["config"]["llm_api_key"] = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        return d


@router.patch("/tenants/{tenant_id}/config")
async def update_tenant_config(tenant_id: str, req: UpdateTenantConfigRequest, request: Request):
    """
    更新租户配置（LLM 端点/模型/密钥 + 技能列表等）
    只更新传入的字段，不覆盖未传入的字段
    """
    from ....infrastructure.persistence.database import async_session_factory
    from ....infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository

    async with async_session_factory() as session:
        repo = SQLAlchemyTenantRepository(session)
        tenant = await repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # 合并配置：只覆盖传入的字段
        config = dict(tenant.config or {})
        updates = req.model_dump(exclude_none=True)
        config.update(updates)

        tenant.update_config(config)
        updated = await repo.update(tenant)
        await session.commit()

        result = updated.to_dict()
        # 脱敏
        if result.get("config", {}).get("llm_api_key"):
            key = result["config"]["llm_api_key"]
            result["config"]["llm_api_key"] = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        return result


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
