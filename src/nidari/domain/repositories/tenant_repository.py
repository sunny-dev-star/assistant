"""
租户仓储接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.tenant import Tenant


class ITenantRepository(ABC):
    """租户仓储接口"""
    
    @abstractmethod
    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """根据 ID 获取租户"""
        pass
    
    @abstractmethod
    async def get_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """根据 API Key 获取租户"""
        pass
    
    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant:
        """创建租户"""
        pass
    
    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        """更新租户"""
        pass
    
    @abstractmethod
    async def delete(self, tenant_id: str) -> bool:
        """删除租户"""
        pass
    
    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """列出所有租户"""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """统计租户数量"""
        pass
