"""
租户领域服务
处理租户相关的核心业务逻辑
"""
from typing import Optional

from ..entities.tenant import Tenant
from ..value_objects.api_key import ApiKey
from ..value_objects.quota import Quota
from ..repositories.tenant_repository import ITenantRepository


class TenantService:
    """租户领域服务"""
    
    def __init__(self, tenant_repo: ITenantRepository):
        self.tenant_repo = tenant_repo
    
    async def create_tenant(
        self,
        name: str,
        industry: Optional[str] = None,
        plan: str = "basic"
    ) -> Tenant:
        """创建新租户"""
        tenant = Tenant(
            name=name,
            industry=industry,
            plan=plan,
            api_key=ApiKey.generate(),
            quota=Quota.default()
        )
        return await self.tenant_repo.create(tenant)
    
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
