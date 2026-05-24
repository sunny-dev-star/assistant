"""
HTTP API 入口 - Claude Skill 规范 + MCP 协议支持
"""
import json
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .infrastructure.config.settings import settings
from .infrastructure.external_services.litellm_adapter import LiteLLMAdapter
from .infrastructure.external_services.tool_gateway_adapter import ToolGatewayAdapter
from .infrastructure.persistence.memory_message_repository import MemoryMessageRepository
from .infrastructure.skill_loader import SkillLoader
from .infrastructure.mcp.client import MCPClient
from .domain.services.conversation_context_service import ConversationContextService
from .app.services.assistant_chat_app_service import AssistantChatAppService

from .ui.http.routes import chat, tenant, health, ecommerce, skills


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 1. LLM Adapter
    llm_adapter = LiteLLMAdapter()
    app.state.llm_adapter = llm_adapter

    # 2. 加载本地技能
    project_root = Path(__file__).resolve().parents[2]
    skills_dir = project_root / "skills"
    skill_loader = SkillLoader(str(skills_dir))
    skill_loader.load_all()

    info = skill_loader.get_skill_info()
    print(f"✅ DeepSeek: {settings.DEEPSEEK_MODEL}")
    print(f"✅ Skills: {skill_loader.skill_count}, Tools: {skill_loader.tool_count}")
    for s in info:
        extras = []
        if s.get("has_references"):
            extras.append("refs")
        if s.get("has_scripts"):
            extras.append("scripts")
        extra = f" [{', '.join(extras)}]" if extras else ""
        print(f"   - {s['id']}: {len(s['tools'])} tools{extra}")

    # 3. MCP Client
    mcp_client = MCPClient()
    if settings.MCP_ENABLED and settings.MCP_SERVERS:
        try:
            servers = json.loads(settings.MCP_SERVERS)
            await mcp_client.connect_servers_from_config(servers)
        except json.JSONDecodeError as e:
            print(f"⚠️ MCP_SERVERS JSON parse error: {e}")
        except Exception as e:
            print(f"⚠️ MCP init error: {e}")

    if mcp_client.server_count > 0:
        print(f"✅ MCP: {mcp_client.server_count} servers, {mcp_client.tool_count} tools")
        for s in mcp_client.get_server_info():
            print(f"   - {s['name']} ({s['transport']}): {s['tools_count']} tools")
    else:
        print("ℹ️ MCP: no servers configured")

    # 4. 初始化仓储与领域服务
    message_repo = MemoryMessageRepository()
    context_service = ConversationContextService()
    tool_gateway = ToolGatewayAdapter(skill_loader, mcp_client)

    # 5. App Service
    assistant_chat_app_service = AssistantChatAppService(
        llm_port=llm_adapter,
        tool_gateway=tool_gateway,
        message_repo=message_repo,
        context_service=context_service
    )
    app.state.assistant_chat_app_service = assistant_chat_app_service
    app.state.skill_loader = skill_loader
    app.state.mcp_client = mcp_client

    yield

    # 清理
    await mcp_client.cleanup()


app = FastAPI(
    title="Assistant API",
    description="智能体框架 - Claude Skill 规范 + MCP 协议 + LiteLLM",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["健康检查"])
app.include_router(chat.router, prefix="/v1", tags=["对话"])
app.include_router(skills.router, prefix="/v1", tags=["技能管理"])
app.include_router(tenant.router, prefix="/v1/admin", tags=["租户管理"])
app.include_router(ecommerce.router, prefix="/v1", tags=["电商"])


@app.get("/")
async def root():
    return {
        "service": "Assistant API",
        "version": "4.0.0",
        "llm": "LiteLLM Unified Gateway",
        "skill_spec": "Claude Skill (Progressive Disclosure)",
        "mcp": "Model Context Protocol",
        "docs": "/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={
        "code": 5000, "message": f"Internal error: {str(exc)}", "data": None
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000,
                reload=settings.ENV == "development")
