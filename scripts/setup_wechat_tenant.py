#!/usr/bin/env python3
"""
Create or update a Nidari tenant with WeChat Official Account configuration.

Usage:
  export DATABASE_URL="postgresql+asyncpg://agent:changeme@localhost:5432/agent_db"
  export WECHAT_TOKEN="your_token"
  export WECHAT_APP_ID="wx..."
  export WECHAT_APP_SECRET="your_secret"
  python3 scripts/setup_wechat_tenant.py

Optional env:
  TENANT_ID       default: tnt_wechat_demo
  TENANT_NAME     default: WeChat Demo Tenant
  ENABLED_SKILLS  comma-separated, default: weather_query,express_query
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid


async def main() -> int:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL is required", file=sys.stderr)
        return 1

    token = os.getenv("WECHAT_TOKEN", "")
    app_id = os.getenv("WECHAT_APP_ID", "")
    app_secret = os.getenv("WECHAT_APP_SECRET", "")
    if not token or not app_id or not app_secret:
        print("ERROR: WECHAT_TOKEN, WECHAT_APP_ID, WECHAT_APP_SECRET are required", file=sys.stderr)
        return 1

    tenant_id = os.getenv("TENANT_ID", "tnt_wechat_demo")
    tenant_name = os.getenv("TENANT_NAME", "WeChat Demo Tenant")
    skills = [s.strip() for s in os.getenv("ENABLED_SKILLS", "weather_query,express_query").split(",") if s.strip()]

    wechat_config = {
        "token": token,
        "app_id": app_id,
        "app_secret": app_secret,
        "encoding_aes_key": os.getenv("WECHAT_ENCODING_AES_KEY", ""),
    }
    tenant_config = {
        "wechat": wechat_config,
        "enabled_skills": skills,
        "window_size": int(os.getenv("WINDOW_SIZE", "10")),
        "default_model": os.getenv("DEFAULT_MODEL", "deepseek/deepseek-chat"),
    }

    # Lazy import after env is set (settings reads DATABASE_URL)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from nidari.infrastructure.persistence.database import async_session_factory
    from nidari.infrastructure.persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository
    from nidari.domain.entities.tenant import Tenant
    from nidari.domain.value_objects.api_key import ApiKey
    from nidari.domain.value_objects.quota import Quota

    async with async_session_factory() as session:
        repo = SQLAlchemyTenantRepository(session)
        existing = await repo.get_by_id(tenant_id)
        if existing:
            cfg = dict(existing.config or {})
            cfg.update(tenant_config)
            existing.update_config(cfg)
            await repo.update(existing)
            await session.commit()
            print(f"Updated tenant: {tenant_id}")
            print(f"Webhook URL path: /webhook/wechat/{tenant_id}")
            return 0

        api_key = os.getenv("TENANT_API_KEY") or f"ak_{uuid.uuid4().hex[:24]}"
        tenant = Tenant(
            id=tenant_id,
            name=tenant_name,
            plan="professional",
            status="active",
            api_key=ApiKey(api_key),
            quota=Quota(limit=1_000_000, used=0),
            config=tenant_config,
        )
        await repo.create(tenant)
        await session.commit()
        print(f"Created tenant: {tenant_id}")
        print(f"API Key: {api_key}")
        print(f"Webhook URL path: /webhook/wechat/{tenant_id}")
        print(f"Config: {json.dumps(tenant_config, ensure_ascii=False, indent=2)}")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
