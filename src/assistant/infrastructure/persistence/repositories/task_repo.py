"""
Scheduled Task repository
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from ..models.scheduled_task_model import ScheduledTaskModel, TaskExecutionLogModel


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, task_id: str) -> Optional[dict]:
        result = await self.session.execute(
            select(ScheduledTaskModel).where(ScheduledTaskModel.id == task_id)
        )
        model = result.scalar_one_or_none()
        return self._to_dict(model) if model else None

    async def get_all_active(self) -> List[dict]:
        result = await self.session.execute(
            select(ScheduledTaskModel).where(ScheduledTaskModel.is_active == True)
        )
        return [self._to_dict(m) for m in result.scalars().all()]

    async def get_by_user(self, tenant_id: str, user_id: str) -> List[dict]:
        result = await self.session.execute(
            select(ScheduledTaskModel).where(
                ScheduledTaskModel.tenant_id == tenant_id,
                ScheduledTaskModel.user_id == user_id,
                ScheduledTaskModel.is_active == True,
            )
        )
        return [self._to_dict(m) for m in result.scalars().all()]

    async def create(self, task: dict) -> dict:
        model = ScheduledTaskModel(**{k: v for k, v in task.items() if v is not None})
        self.session.add(model)
        await self.session.flush()
        return self._to_dict(model)

    async def update_after_run(self, task_id: str, result: str, error: Optional[str] = None):
        values = {
            "last_run_at": datetime.utcnow(),
            "run_count": ScheduledTaskModel.run_count + 1,
        }
        if error:
            values["error_count"] = ScheduledTaskModel.error_count + 1
            values["last_error"] = error
        else:
            values["last_result"] = result
            values["last_error"] = None

        await self.session.execute(
            update(ScheduledTaskModel).where(ScheduledTaskModel.id == task_id).values(**values)
        )
        await self.session.flush()

    async def deactivate(self, task_id: str):
        await self.session.execute(
            update(ScheduledTaskModel).where(ScheduledTaskModel.id == task_id).values(is_active=False)
        )
        await self.session.flush()

    async def create_log(self, task_id: str, tenant_id: str) -> int:
        log = TaskExecutionLogModel(task_id=task_id, tenant_id=tenant_id, status="running")
        self.session.add(log)
        await self.session.flush()
        return log.id

    async def finish_log(self, log_id: int, result: Optional[str], error: Optional[str]):
        values = {"finished_at": datetime.utcnow(), "status": "failed" if error else "success"}
        if result:
            values["result"] = result[:4000]
        if error:
            values["error_detail"] = error[:4000]
        await self.session.execute(
            update(TaskExecutionLogModel).where(TaskExecutionLogModel.id == log_id).values(**values)
        )
        await self.session.flush()

    def _to_dict(self, model: ScheduledTaskModel) -> dict:
        return {c.name: getattr(model, c.name) for c in model.__table__.columns}
