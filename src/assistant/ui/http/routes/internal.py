"""
Internal API for scheduled tasks (called by skill scripts)
"""
import os
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/internal")

INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "")


def verify_internal(request: Request):
    """Internal endpoint auth — shared secret or disabled in dev"""
    if INTERNAL_TOKEN and request.headers.get("X-Internal-Token") != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid internal token")


class CreateTaskBody(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    channel: str = "wechat"
    task_type: str
    display_name: str = ""
    execution_type: str = "message"
    cron_expr: Optional[str] = None
    run_once_at: Optional[str] = None
    message: Optional[str] = None
    skill_name: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: dict = {}
    steps: list = []
    mission_prompt: Optional[str] = None
    mission_skills: list = []
    context_as_input: bool = False
    result_as_message: bool = True
    skill_disabled_action: str = "notify_admin"


@router.post("/tasks", dependencies=[Depends(verify_internal)])
async def create_task(body: CreateTaskBody, request: Request):
    """Create a new scheduled task"""
    from ...infrastructure.persistence.database import async_session_factory
    from ...infrastructure.persistence.repositories.task_repo import TaskRepository

    async with async_session_factory() as session:
        repo = TaskRepository(session)
        task = await repo.create(body.model_dump(exclude_none=True))
        await session.commit()

    scheduler = request.app.state.scheduler
    scheduler.register_new(task)
    return {"task_id": task["id"], "status": "scheduled"}


@router.get("/tasks", dependencies=[Depends(verify_internal)])
async def list_tasks(
    request: Request,
    tenant_id: str = Query(...),
    user_id: str = Query(...),
    limit: int = Query(10),
):
    """List user's active tasks"""
    from ...infrastructure.persistence.database import async_session_factory
    from ...infrastructure.persistence.repositories.task_repo import TaskRepository

    async with async_session_factory() as session:
        repo = TaskRepository(session)
        tasks = await repo.get_by_user(tenant_id, user_id)
    return {"tasks": tasks[:limit]}


@router.delete("/tasks/{task_id}", dependencies=[Depends(verify_internal)])
async def cancel_task(
    task_id: str,
    request: Request,
    tenant_id: str = Query(...),
    user_id: str = Query(...),
):
    """Cancel a task (ownership check)"""
    from ...infrastructure.persistence.database import async_session_factory
    from ...infrastructure.persistence.repositories.task_repo import TaskRepository

    async with async_session_factory() as session:
        repo = TaskRepository(session)
        task = await repo.get_by_id(task_id)

        if not task or task["tenant_id"] != tenant_id or task["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        await repo.deactivate(task_id)
        await session.commit()

    request.app.state.scheduler.cancel(task_id)
    return {"status": "cancelled", "task_id": task_id}
