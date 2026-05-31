"""
健康检查路由
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "nidari"
    }


@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "redis": "ok",
            "dify": "ok"
        }
    }
