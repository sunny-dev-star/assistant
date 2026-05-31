"""
Role & permission repository
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional

from ..models.role_model import (
    RoleModel, RoleSkillGrantModel, UserRoleModel
)


class RoleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── 角色 CRUD ─────────────────────────────────────────

    async def create(self, role: dict) -> dict:
        model = RoleModel(**role)
        self.session.add(model)
        await self.session.flush()
        return self._to_dict(model)

    async def get_by_id(self, role_id: str) -> Optional[dict]:
        result = await self.session.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        m = result.scalar_one_or_none()
        return self._to_dict(m) if m else None

    async def get_by_tenant(self, tenant_id: str) -> list[dict]:
        result = await self.session.execute(
            select(RoleModel).where(RoleModel.tenant_id == tenant_id)
        )
        return [self._to_dict(r) for r in result.scalars().all()]

    async def get_default_role(self, tenant_id: str) -> Optional[dict]:
        result = await self.session.execute(
            select(RoleModel).where(
                RoleModel.tenant_id == tenant_id,
                RoleModel.is_default == True
            )
        )
        m = result.scalar_one_or_none()
        return self._to_dict(m) if m else None

    async def delete_role(self, role_id: str):
        await self.session.execute(
            delete(RoleModel).where(RoleModel.id == role_id)
        )
        await self.session.flush()

    # ── 技能授权 ──────────────────────────────────────────

    async def grant_skill(self, role_id: str, skill_name: str,
                          tool_whitelist: list | None,
                          granted_by: str = None):
        """授予角色技能权限（存在则更新）"""
        existing = await self.session.execute(
            select(RoleSkillGrantModel).where(
                RoleSkillGrantModel.role_id == role_id,
                RoleSkillGrantModel.skill_name == skill_name,
            )
        )
        model = existing.scalar_one_or_none()
        if model:
            model.tool_whitelist = tool_whitelist
            model.granted_by = granted_by
        else:
            self.session.add(RoleSkillGrantModel(
                role_id=role_id,
                skill_name=skill_name,
                tool_whitelist=tool_whitelist,
                granted_by=granted_by,
            ))
        await self.session.flush()

    async def revoke_skill(self, role_id: str, skill_name: str):
        await self.session.execute(
            delete(RoleSkillGrantModel).where(
                RoleSkillGrantModel.role_id == role_id,
                RoleSkillGrantModel.skill_name == skill_name,
            )
        )
        await self.session.flush()

    async def get_grants_by_role(self, role_id: str) -> list[dict]:
        result = await self.session.execute(
            select(RoleSkillGrantModel).where(
                RoleSkillGrantModel.role_id == role_id
            )
        )
        return [{"skill_name": r.skill_name,
                 "tool_whitelist": r.tool_whitelist}
                for r in result.scalars().all()]

    # ── 用户角色绑定 ──────────────────────────────────────

    async def assign_role(self, tenant_id: str, user_id: str,
                          role_id: str, assigned_by: str = None):
        model = UserRoleModel(
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        await self.session.merge(model)
        await self.session.flush()

    async def unassign_role(self, tenant_id: str, user_id: str, role_id: str):
        await self.session.execute(
            delete(UserRoleModel).where(
                UserRoleModel.tenant_id == tenant_id,
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role_id,
            )
        )
        await self.session.flush()

    async def get_user_roles(self, tenant_id: str,
                             user_id: str) -> list[dict]:
        result = await self.session.execute(
            select(RoleModel).join(
                UserRoleModel,
                UserRoleModel.role_id == RoleModel.id
            ).where(
                UserRoleModel.tenant_id == tenant_id,
                UserRoleModel.user_id == user_id,
            )
        )
        return [self._to_dict(r) for r in result.scalars().all()]

    # ── 核心：获取用户有效权限（合并多角色）──────────────

    async def get_effective_grants(
        self, tenant_id: str, user_id: str
    ) -> dict[str, list | None]:
        """
        返回用户在该租户下的有效技能权限。
        多角色时取并集，工具白名单也合并（任一角色无限制则合并后无限制）。

        返回格式：
        {
            "elder_care": None,          # None = 所有工具可用
            "weather_query": ["get_weather"],  # 只能用这个工具
        }
        """
        user_role_list = await self.get_user_roles(tenant_id, user_id)

        if not user_role_list:
            # 用户无角色 → 使用租户 default 角色
            default = await self.get_default_role(tenant_id)
            if not default:
                return {}
            user_role_list = [default]

        # 管理员角色：返回特殊标记，上层处理
        if any(r.get("is_admin") for r in user_role_list):
            return {"__admin__": None}

        # 合并所有角色的技能授权
        merged: dict[str, set | None] = {}

        for role in user_role_list:
            grants = await self.get_grants_by_role(role["id"])
            for grant in grants:
                skill = grant["skill_name"]
                wl = grant["tool_whitelist"]  # None 或 list

                if skill not in merged:
                    merged[skill] = set(wl) if wl else None
                else:
                    if merged[skill] is None or wl is None:
                        merged[skill] = None  # 任一角色无限制 → 合并无限制
                    else:
                        merged[skill] = merged[skill] | set(wl)  # 取并集

        return {k: list(v) if v is not None else None
                for k, v in merged.items()}

    def _to_dict(self, model) -> dict:
        if model is None:
            return None
        return {c.name: getattr(model, c.name)
                for c in model.__table__.columns}
