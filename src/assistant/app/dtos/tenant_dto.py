"""
租户相关的 DTO
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class CreateTenantDTO:
    """创建租户 DTO"""
    name: str
    industry: Optional[str] = None
    contact: Optional[str] = None
    plan: str = "basic"
    config: Optional[Dict[str, Any]] = None


@dataclass
class TenantResponseDTO:
    """租户响应 DTO"""
    tenant_id: str
    name: str
    industry: Optional[str]
    plan: str
    status: str
    api_key: str
    quota: Dict[str, Any]
    created_at: str


@dataclass
class UpdateTenantDTO:
    """更新租户 DTO"""
    name: Optional[str] = None
    industry: Optional[str] = None
    contact: Optional[str] = None
    plan: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


@dataclass
class TenantStatsDTO:
    """租户统计 DTO"""
    tenant_id: str
    total_conversations: int
    total_messages: int
    tokens_used_this_month: int
    quota_remaining: int
    active_channels: list
