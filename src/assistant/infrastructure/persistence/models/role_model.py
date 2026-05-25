"""
Role & permission ORM models
"""
from sqlalchemy import Column, String, Boolean, Text, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func

from ..database import Base


class RoleModel(Base):
    """角色定义表 — 每个租户维护自己的角色体系"""
    __tablename__ = "roles"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    display_name = Column(String(100))
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RoleSkillGrantModel(Base):
    """角色技能授权表 — 控制角色能用哪个技能的哪些工具"""
    __tablename__ = "role_skill_grants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(String(50), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String(50), nullable=False)
    # NULL → 该技能所有工具均可用; [...] → 只能使用白名单内的工具
    tool_whitelist = Column(JSON, nullable=True)
    granted_at = Column(DateTime, server_default=func.now())
    granted_by = Column(String(50))


class UserRoleModel(Base):
    """用户角色绑定表 — 一个用户可绑定多个角色，权限取并集"""
    __tablename__ = "user_roles"

    tenant_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), primary_key=True)
    role_id = Column(String(50), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime, server_default=func.now())
    assigned_by = Column(String(50))
