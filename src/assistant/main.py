"""
HTTP API entry point - Multi-tenant with auth middleware + DB persistence + role-based permissions
"""
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .infrastructure.config.settings import settings
from .infrastructure.external_services.litellm_adapter import LiteLLMAdapter
from .infrastructure.external_services.tool_gateway_adapter import ToolGatewayAdapter
from .infrastructure.persistence.database_message_repository import DatabaseMessageRepository
from .infrastructure.persistence.memory_message_repository import MemoryMessageRepository
from .infrastructure.skill_loader import SkillLoader
from .infrastructure.mcp.client import MCPClient
from .domain.services.conversation_context_service import ConversationContextService
from .app.services.assistant_chat_app_service import ConversationAppService
from .infrastructure.middleware.tenant_auth import TenantAuthMiddleware

from .ui.http.routes import chat, tenant, health, ecommerce, skills, wechat, billing, outbound, internal, roles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle"""
    use_db = "postgresql" in settings.DATABASE_URL or "sqlite" in settings.DATABASE_URL

    # 1. Init database
    if use_db:
        from .infrastructure.persistence.database import init_db
        try:
            await init_db()
            print("[Init] Database tables ensured.")
        except Exception as e:
            print(f"[Warning] DB init failed, falling back to in-memory: {e}")
            use_db = False

    # 2. LLM Adapter
    llm_adapter = LiteLLMAdapter()

    # 3. Load local skills
    project_root = Path(__file__).resolve().parents[2]
    skills_dir = project_root / "skills"
    skill_loader = SkillLoader(str(skills_dir))
    skill_loader.load_all()

    info = skill_loader.get_skill_info()
    print(f"[Init] LLM model: {settings.DEEPSEEK_MODEL}")
    print(f"[Init] Skills: {skill_loader.skill_count}, Tools: {skill_loader.tool_count}")
    for s in info:
        extras = []
        if s.get("has_references"):
            extras.append("refs")
        if s.get("has_scripts"):
            extras.append("scripts")
        extra = f" [{', '.join(extras)}]" if extras else ""
        print(f"  - {s['id']}: {len(s['tools'])} tools{extra}")

    # 4. MCP Client
    mcp_client = MCPClient()
    if settings.MCP_ENABLED and settings.MCP_SERVERS:
        try:
            servers = json.loads(settings.MCP_SERVERS)
            await mcp_client.connect_servers_from_config(servers)
        except json.JSONDecodeError as e:
            print(f"[Warning] MCP_SERVERS JSON parse error: {e}")
        except Exception as e:
            print(f"[Warning] MCP init error: {e}")

    if mcp_client.server_count > 0:
        print(f"[Init] MCP: {mcp_client.server_count} servers, {mcp_client.tool_count} tools")

    # 5. Repositories - use DB-backed when available
    if use_db:
        message_repo = DatabaseMessageRepository()
        print("[Init] Message repository: Database (SQLite)")
    else:
        message_repo = MemoryMessageRepository()
        print("[Init] Message repository: In-Memory")

    context_service = ConversationContextService(llm_port=llm_adapter)

    # Tool gateway — DB 模式下注入 role_repo_factory
    role_repo_factory = None
    if use_db:
        from .infrastructure.persistence.database import async_session_factory
        from .infrastructure.persistence.repositories.role_repo import RoleRepository
        role_repo_factory = lambda session: RoleRepository(session)
    tool_gateway = ToolGatewayAdapter(skill_loader, mcp_client, role_repo_factory)

    # 6. App Service
    assistant_chat_app_service = ConversationAppService(
        llm_port=llm_adapter,
        tool_gateway=tool_gateway,
        message_repo=message_repo,
        context_service=context_service
    )

    # Store in app.state
    app.state.assistant_chat_app_service = assistant_chat_app_service
    app.state.skill_loader = skill_loader
    app.state.mcp_client = mcp_client
    app.state.llm_adapter = llm_adapter
    app.state.use_db = use_db

    # 7. TaskScheduler (replaces old outbound scheduler)
    from .infrastructure.scheduler import TaskScheduler
    from .infrastructure.alerting.feishu_alert import FeishuAlerter
    feishu_alerter = FeishuAlerter(webhook_url=settings.FEISHU_WEBHOOK_URL if hasattr(settings, 'FEISHU_WEBHOOK_URL') else "")
    scheduler = TaskScheduler(app_service=assistant_chat_app_service, alerter=feishu_alerter)
    await scheduler.start()
    app.state.scheduler = scheduler
    print(f"[Init] TaskScheduler: {scheduler.job_count} tasks restored")

    if use_db:
        print("[Init] Role-based permissions: enabled (DB-backed)")

    auth_status = "ON (Bearer token required)" if settings.AUTH_ENABLED else "OFF (dev mode, auto-tenant)"
    print(f"[Init] Auth: {auth_status}")
    print("=== Assistant API v5.0 ready ===")

    yield

    # Cleanup
    scheduler = getattr(app.state, 'scheduler', None)
    if scheduler:
        scheduler.shutdown()
    await mcp_client.cleanup()


app = FastAPI(
    title="Assistant API",
    description="Multi-tenant AI Agent Framework",
    version="5.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenantAuthMiddleware)

app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(skills.router, prefix="/v1", tags=["Skills"])
app.include_router(tenant.router, prefix="/v1/admin", tags=["Tenant Admin"])
app.include_router(roles.router, prefix="/v1/admin/roles", tags=["Role Management"])
app.include_router(ecommerce.router, prefix="/v1", tags=["Ecommerce"])
app.include_router(wechat.router, prefix="/webhook", tags=["WeChat Webhook"])
app.include_router(billing.router, prefix="/v1/admin", tags=["Billing & Usage"])
app.include_router(outbound.router, prefix="/v1/admin", tags=["Outbound Scheduler"])
app.include_router(internal.router, tags=["Internal"])


@app.get("/")
async def root():
    return {
        "service": "Assistant API",
        "version": "5.0.0",
        "features": ["multi-tenant", "skill-sdk", "mcp", "litellm", "role-permissions"],
        "auth_enabled": settings.AUTH_ENABLED,
        "persistence": "database" if settings.DATABASE_URL else "none",
        "docs": "/docs",
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from starlette.responses import Response as StarletteResponse

    try:
        from .infrastructure.metrics import app_info
        app_info.info({"version": "5.0.0", "service": "assistant-api"})
    except Exception:
        pass

    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger(__name__).error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={
        "code": 5000, "message": f"Internal error: {str(exc)}", "data": None
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000,
                reload=settings.ENV == "development")
