"""Tenant frontend config repository"""
from sqlalchemy import select
from ..models.bff_models import TenantFrontendConfigModel


class TenantFrontendConfigRepository:
    def __init__(self, session):
        self.session = session

    async def get(self, tenant_id: str) -> dict | None:
        stmt = select(TenantFrontendConfigModel).where(
            TenantFrontendConfigModel.tenant_id == tenant_id
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        if not result:
            # Return defaults
            return {
                "app_name": "智能助手",
                "logo_url": None,
                "primary_color": "#1890ff",
                "welcome_message": "你好，有什么可以帮你？",
                "features": {},
                "web_theme": {},
                "auth_methods": {"wechat": True, "phone": True, "email": False, "feishu": False, "dingtalk": False},
                "streaming_enabled": False,
                "jwt_secret": "change-me-in-production",
            }
        return {
            "app_name": result.app_name,
            "logo_url": result.logo_url,
            "primary_color": result.primary_color,
            "welcome_message": result.welcome_message,
            "features": result.features or {},
            "web_theme": result.web_theme or {},
            "auth_methods": result.auth_methods or {},
            "streaming_enabled": result.streaming_enabled,
            "jwt_secret": "change-me-in-production",  # Should come from tenant config
        }

    async def upsert(self, tenant_id: str, data: dict) -> dict:
        stmt = select(TenantFrontendConfigModel).where(
            TenantFrontendConfigModel.tenant_id == tenant_id
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        if result:
            for k, v in data.items():
                if hasattr(result, k):
                    setattr(result, k, v)
        else:
            import uuid
            result = TenantFrontendConfigModel(
                id=f"tfc_{uuid.uuid4().hex[:10]}",
                tenant_id=tenant_id,
                **data,
            )
            self.session.add(result)
        await self.session.flush()
        return await self.get(tenant_id)
