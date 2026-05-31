"""
角色与权限管理路由
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


# ── 数据模型 ─────────────────────────────────────────────────

class CreateRoleBody(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    is_default: bool = False
    is_admin: bool = False


class GrantSkillBody(BaseModel):
    skill_name: str
    tool_whitelist: list[str] | None = None  # None = 所有工具


class AssignRoleBody(BaseModel):
    user_id: str
    role_id: str


# ── 角色管理 ─────────────────────────────────────────────────

@router.post("")
async def create_role(body: CreateRoleBody, request: Request):
    """创建角色"""
    tenant = request.state.tenant
    import uuid
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        role = await role_repo.create({
            "id": f"role_{uuid.uuid4().hex[:8]}",
            "tenant_id": tenant.id,
            "name": body.name,
            "display_name": body.display_name or body.name,
            "description": body.description,
            "is_default": body.is_default,
            "is_admin": body.is_admin,
        })
        await session.commit()
        return role


@router.get("")
async def list_roles(request: Request):
    """列出租户所有角色"""
    tenant = request.state.tenant
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        roles = await role_repo.get_by_tenant(tenant.id)
        return {"roles": roles}


@router.get("/{role_id}")
async def get_role(role_id: str, request: Request):
    """获取角色详情"""
    tenant = request.state.tenant
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        role = await role_repo.get_by_id(role_id)
        if not role or role["tenant_id"] != tenant.id:
            raise HTTPException(404, "角色不存在")
        grants = await role_repo.get_grants_by_role(role_id)
        role["grants"] = grants
        return role


@router.delete("/{role_id}")
async def delete_role(role_id: str, request: Request):
    """删除角色"""
    tenant = request.state.tenant
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        role = await role_repo.get_by_id(role_id)
        if not role or role["tenant_id"] != tenant.id:
            raise HTTPException(404, "角色不存在")
        await role_repo.delete_role(role_id)
        await session.commit()
        return {"status": "deleted"}


# ── 技能授权 ─────────────────────────────────────────────────

@router.post("/{role_id}/skills")
async def grant_skill(role_id: str, body: GrantSkillBody, request: Request):
    """授予角色技能权限"""
    tenant = request.state.tenant

    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)

        # 校验 role 属于本租户
        roles = await role_repo.get_by_tenant(tenant.id)
        if not any(r["id"] == role_id for r in roles):
            raise HTTPException(404, "角色不存在")

        # 校验技能已被租户购买（platform 技能除外）
        loader = request.app.state.skill_loader
        tenant_enabled = set(tenant.config.get("enabled_skills", []))
        if (body.skill_name not in loader._platform
                and body.skill_name not in loader._industry):
            raise HTTPException(400, f"技能 {body.skill_name} 不存在")
        if (body.skill_name not in loader._platform
                and body.skill_name not in tenant_enabled):
            raise HTTPException(400, f"租户未购买技能 {body.skill_name}")

        operator_id = getattr(request.state, 'operator_id', 'system')
        await role_repo.grant_skill(
            role_id, body.skill_name,
            body.tool_whitelist,
            granted_by=operator_id,
        )
        await session.commit()
        return {"status": "granted"}


@router.delete("/{role_id}/skills/{skill_name}")
async def revoke_skill(role_id: str, skill_name: str, request: Request):
    """撤销角色技能权限"""
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        await role_repo.revoke_skill(role_id, skill_name)
        await session.commit()
        return {"status": "revoked"}


@router.get("/{role_id}/skills")
async def list_role_skills(role_id: str, request: Request):
    """列出角色已授权的技能"""
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        grants = await role_repo.get_grants_by_role(role_id)
        return {"grants": grants}


# ── 用户角色绑定 ─────────────────────────────────────────────

@router.post("/users/assign")
async def assign_role(body: AssignRoleBody, request: Request):
    """绑定用户角色"""
    tenant = request.state.tenant
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        operator_id = getattr(request.state, 'operator_id', 'system')
        await role_repo.assign_role(
            tenant.id, body.user_id, body.role_id,
            assigned_by=operator_id,
        )
        await session.commit()
        return {"status": "assigned"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def unassign_role(user_id: str, role_id: str, request: Request):
    """解绑用户角色"""
    tenant = request.state.tenant
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        await role_repo.unassign_role(tenant.id, user_id, role_id)
        await session.commit()
        return {"status": "unassigned"}


@router.get("/users/{user_id}/roles")
async def get_user_roles(user_id: str, request: Request):
    """查询用户角色"""
    tenant = request.state.tenant
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        roles = await role_repo.get_user_roles(tenant.id, user_id)
        return {"roles": roles}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: str, request: Request):
    """查询用户有效权限（合并多角色后的技能+工具权限）"""
    tenant = request.state.tenant
    async with _get_session() as session:
        from ....infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo = RoleRepository(session)
        grants = await role_repo.get_effective_grants(tenant.id, user_id)
        return {"grants": grants}


# ── 工具函数 ─────────────────────────────────────────────────

from contextlib import asynccontextmanager
from ....infrastructure.persistence.database import async_session_factory


@asynccontextmanager
async def _get_session():
    """获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
