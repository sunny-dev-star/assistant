"""
HTTP API 入口
FastAPI 应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ...infrastructure.config.settings import settings
from ...infrastructure.external_services.dify_client import DifyClient

from .routes import chat, tenant, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    app.state.dify_client = DifyClient(
        base_url=settings.DIFY_API_URL,
        api_key=settings.DIFY_API_KEY
    )
    
    yield
    
    # 关闭时
    await app.state.dify_client.close()


app = FastAPI(
    title="Assistant API",
    description="智能体框架 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(chat.router, prefix="/v1", tags=["对话"])
app.include_router(tenant.router, prefix="/v1/admin", tags=["租户管理"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "code": 5000,
            "message": f"Internal error: {str(exc)}",
            "data": None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENV == "development"
    )
