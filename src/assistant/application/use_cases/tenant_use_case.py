"""
租户用例
"""
from typing import Optional, List

from ...domain.entities.tenant import Tenant
from ...domain.services.tenant_service import TenantService
from ...domain.repositories.tenant_repository import ITenantRepository

from ..dtos.tenant_dto import (
    CreateTenantDTO,
    TenantResponseDTO,
    UpdateTenantDTO,
    TenantStatsDTO
)


class TenantUseCase:
    """租户用例"""
    
    def __init__(
        self,
        tenant_service: TenantService,
        tenant_repo: ITenantRepository
    ):
        self.tenant_service = tenant_service
        self.tenant_repo = tenant_repo
    
    async def create_tenant(self, dto: CreateTenantDTO) -> TenantResponseDTO:
        """创建租户"""
        tenant = await self.tenant_service.create_tenant(
            name=dto.name,
            industry=dto.industry,
            plan=dto.plan
        )
        
        if dto.config:
            tenant.update_config(dto.config)
            await self.tenant_repo.update(tenant)
        
        return self._to_response_dto(tenant)
    
    async def get_tenant(self, tenant_id: str) -> Optional[TenantResponseDTO]:
        """获取租户"""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return None
        
        return self._to_response_dto(tenant)
    
    async def list_tenants(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[TenantResponseDTO]:
        """列出租户"""
        tenants = await self.tenant_repo.list_all(skip=skip, limit=limit)
        return [self._to_response_dto(t) for t in tenants]
    
    async def update_tenant(
        self,
        tenant_id: str,
        dto: UpdateTenantDTO
    ) -> Optional[TenantResponseDTO]:
        """更新租户"""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return None
        
        if dto.name:
            tenant.name = dto.name
        if dto.industry:
            tenant.industry = dto.industry
        if dto.contact:
            tenant.contact = dto.contact
        if dto.plan:
            tenant.plan = dto.plan
        if dto.config:
            tenant.update_config(dto.config)
        
        updated = await self.tenant_repo.update(tenant)
        return self._to_response_dto(updated)
    
    async def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户"""
        return await self.tenant_repo.delete(tenant_id)
    
    async def get_tenant_stats(self, tenant_id: str) -> Optional[TenantStatsDTO]:
        """获取租户统计"""
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return None
        
        quota_status = tenant.quota.to_dict()
        
        return TenantStatsDTO(
            tenant_id=tenant.id,
            total_conversations=0,  # TODO: 从仓储查询
            total_messages=0,       # TODO: 从仓储查询
            tokens_used_this_month=quota_status["used"],
            quota_remaining=quota_status["remaining"],
            active_channels=[]      # TODO: 从仓储查询
        )
    
    def _to_response_dto(self, tenant: Tenant) -> TenantResponseDTO:
        """转换为响应 DTO"""
        return TenantResponseDTO(
            tenant_id=tenant.id,
            name=tenant.name,
            industry=tenant.industry,
            plan=tenant.plan,
            status=tenant.status,
            api_key=tenant.api_key.value,
            quota=tenant.quota.to_dict(),
            created_at=tenant.created_at.isoformat()
        )
