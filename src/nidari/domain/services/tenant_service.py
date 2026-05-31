"""
租户领域服务
处理租户相关的核心业务逻辑
"""
import uuid
import secrets
from typing import Optional

from ..entities.tenant import Tenant
from ..value_objects.api_key import ApiKey
from ..value_objects.quota import Quota
from ..repositories.tenant_repository import ITenantRepository


class TenantService:
    """租户领域服务"""
    
    def __init__(self, tenant_repo: ITenantRepository, role_repo=None):
        self.tenant_repo = tenant_repo
        self.role_repo = role_repo

    def set_role_repo(self, role_repo):
        """延迟注入角色仓储"""
        self.role_repo = role_repo
    
    async def create_tenant(
        self,
        name: str,
        industry: Optional[str] = None,
        plan: str = "basic",
        config: dict = None
    ) -> dict:
        """
        创建租户，同时初始化两个默认角色（admin + default）
        返回包含 api_key 的完整信息
        """
        tenant_id = f"tnt_{uuid.uuid4().hex[:8]}"
        api_key = f"ak_{secrets.token_hex(16)}"

        # 1. 创建租户记录
        tenant = Tenant(
            id=tenant_id,
            name=name,
            industry=industry,
            plan=plan,
            api_key=ApiKey(api_key),
            quota=Quota.default(),
        )
        if config:
            tenant.config = config
        created_tenant = await self.tenant_repo.create(tenant)

        # 2. 创建管理员角色（绕过技能白名单）
        admin_role = None
        default_role = None
        if self.role_repo:
            try:
                admin_role = await self.role_repo.create({
                    "id": f"role_{uuid.uuid4().hex[:8]}",
                    "tenant_id": tenant_id,
                    "name": "admin",
                    "display_name": "管理员",
                    "description": "可使用租户所有已购技能",
                    "is_default": False,
                    "is_admin": True,
                })

                # 3. 创建默认用户角色（无技能权限，需手动授权）
                default_role = await self.role_repo.create({
                    "id": f"role_{uuid.uuid4().hex[:8]}",
                    "tenant_id": tenant_id,
                    "name": "default",
                    "display_name": "普通用户",
                    "description": "默认角色，需管理员授权具体技能",
                    "is_default": True,
                    "is_admin": False,
                })
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to create default roles: {e}")

        return {
            "tenant": created_tenant,
            "admin_role": admin_role,
            "default_role": default_role,
            "api_key": api_key,
        }

    async def authenticate(self, api_key: str) -> Optional[Tenant]:
        """验证 API Key"""
        tenant = await self.tenant_repo.get_by_api_key(api_key)
        if not tenant:
            return None
        
        if not tenant.is_active():
            return None
        
        return tenant
    
    async def consume_quota(self, tenant_id: str, tokens: int) -> bool:
        """消耗租户配额"""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return False
        
        if not tenant.has_quota(tokens):
            return False
        
        tenant.consume_quota(tokens)
        await self.tenant_repo.update(tenant)
        return True
    
    async def get_quota_status(self, tenant_id: str) -> dict:
        """获取配额状态"""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return {}
        
        return tenant.quota.to_dict()
    
    async def update_tenant_config(
        self,
        tenant_id: str,
        config: dict
    ) -> Optional[Tenant]:
        """更新租户配置"""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return None
        
        tenant.update_config(config)
        return await self.tenant_repo.update(tenant)
    
    async def suspend_tenant(self, tenant_id: str) -> bool:
        """暂停租户"""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return False
        
        tenant.suspend()
        await self.tenant_repo.update(tenant)
        return True
    
    async def activate_tenant(self, tenant_id: str) -> bool:
        """激活租户"""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return False
        
        tenant.activate()
        await self.tenant_repo.update(tenant)
        return True
