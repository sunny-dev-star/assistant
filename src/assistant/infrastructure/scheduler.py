"""
TaskScheduler — persistent scheduled task engine with 4 execution modes
"""
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from .persistence.database import async_session_factory
from .persistence.repositories.task_repo import TaskRepository
from .persistence.sqlalchemy_tenant_repository import SQLAlchemyTenantRepository

logger = logging.getLogger(__name__)


class SkillNotAvailableError(Exception):
    def __init__(self, skill: str, tenant_id: str, task_id: str):
        self.skill = skill
        self.tenant_id = tenant_id
        self.task_id = task_id
        super().__init__(f"Skill '{skill}' not available for tenant '{tenant_id}'")


class TaskScheduler:
    def __init__(self, app_service=None, alerter=None):
        self._scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self._app_service = app_service
        self._alerter = alerter

    def configure(self, app_service=None, alerter=None):
        if app_service:
            self._app_service = app_service
        if alerter:
            self._alerter = alerter

    async def start(self):
        """Start scheduler and restore tasks from DB"""
        self._scheduler.start()
        async with async_session_factory() as session:
            repo = TaskRepository(session)
            tasks = await repo.get_all_active()
            for task in tasks:
                self._register(task)
        logger.info(f"TaskScheduler started, restored {len(tasks)} tasks")

    def shutdown(self):
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def register_new(self, task: dict):
        self._register(task)
        logger.info(f"New task registered: {task['id']} ({task['execution_type']})")

    def cancel(self, task_id: str):
        try:
            self._scheduler.remove_job(task_id)
            logger.info(f"Task cancelled: {task_id}")
        except Exception:
            pass

    def _register(self, task: dict):
        if task.get("cron_expr"):
            trigger = CronTrigger.from_crontab(
                task["cron_expr"],
                timezone=task.get("timezone", "Asia/Shanghai")
            )
        elif task.get("run_once_at"):
            run_at = task["run_once_at"]
            if isinstance(run_at, str):
                run_at = datetime.fromisoformat(run_at)
            if run_at <= datetime.now():
                logger.warning(f"Task {task['id']} time has passed, skipping")
                return
            trigger = DateTrigger(run_date=run_at)
        else:
            logger.error(f"Task {task['id']} has no valid schedule config")
            return

        self._scheduler.add_job(
            func=self._execute_task,
            trigger=trigger,
            args=[task],
            id=task["id"],
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
        )

    # ==========================================
    # Unified execution entry
    # ==========================================

    async def _execute_task(self, task: dict):
        async with async_session_factory() as session:
            repo = TaskRepository(session)
            log_id = await repo.create_log(task["id"], task["tenant_id"])

            result = None
            error = None
            try:
                handlers = {
                    "message": self._execute_message,
                    "skill_invoke": self._execute_skill_invoke,
                    "pipeline": self._execute_pipeline,
                    "agent_mission": self._execute_agent_mission,
                }
                handler = handlers.get(task["execution_type"])
                if not handler:
                    raise ValueError(f"Unknown execution type: {task['execution_type']}")

                result = await handler(task, repo)

                # Auto-deactivate one-shot tasks
                if task.get("run_once_at"):
                    await repo.deactivate(task["id"])
                    self.cancel(task["id"])

            except SkillNotAvailableError as e:
                error = str(e)
                await self._handle_skill_disabled(task, e)

            except Exception as e:
                error = str(e)
                logger.error(f"Task {task['id']} execution error: {e}", exc_info=True)

            finally:
                await repo.update_after_run(task["id"], result or "", error)
                await repo.finish_log(log_id, result, error)
                await session.commit()

    # ==========================================
    # 4 execution modes
    # ==========================================

    async def _execute_message(self, task: dict, repo) -> str:
        """Mode 1: push fixed text"""
        msg = task.get("message", "")
        logger.info(f"[message] Task {task['id']}: {msg[:50]}")
        # In production, send via channel adapter
        # For now, record in conversation
        return msg

    async def _execute_skill_invoke(self, task: dict, repo) -> str:
        """Mode 2: execute single tool"""
        tenant = await self._get_tenant_and_check_skill(
            task["tenant_id"], task.get("skill_name", ""), task["id"]
        )
        if self._app_service:
            result = await self._app_service.invoke_tool_directly(
                tenant=tenant,
                user_id=task["user_id"],
                channel=task["channel"],
                skill_name=task.get("skill_name", ""),
                tool_name=task.get("tool_name", ""),
                tool_args=task.get("tool_args", {}),
            )
            return result or ""
        return "AppService not available"

    async def _execute_pipeline(self, task: dict, repo) -> str:
        """Mode 3: sequential tool chain"""
        tenant_repo = SQLAlchemyTenantRepository(repo.session)
        tenant = await tenant_repo.get_by_id(task["tenant_id"])
        steps = task.get("steps", [])
        ctx = {}
        final_output = None

        for step in steps:
            skill_name = step.get("skill_name", "")
            # Check skill permission per step
            if skill_name != "platform":
                enabled = tenant.config.get("enabled_skills", [])
                if skill_name not in enabled:
                    raise SkillNotAvailableError(skill_name, task["tenant_id"], task["id"])

            args = dict(step.get("args", {}))
            for key in step.get("inject_results", []):
                if key in ctx:
                    args[f"_prev_{key}"] = ctx[key]

            if self._app_service:
                result = await self._app_service.invoke_tool_directly(
                    tenant=tenant,
                    user_id=task["user_id"],
                    channel=task["channel"],
                    skill_name=skill_name,
                    tool_name=step.get("tool_name", ""),
                    tool_args=args,
                )
            else:
                result = "AppService not available"

            if step.get("result_key"):
                ctx[step["result_key"]] = result
            final_output = result

        return final_output or ""

    async def _execute_agent_mission(self, task: dict, repo) -> str:
        """Mode 4: LLM autonomous orchestration"""
        tenant_repo = SQLAlchemyTenantRepository(repo.session)
        tenant = await tenant_repo.get_by_id(task["tenant_id"])

        enabled = set(tenant.config.get("enabled_skills", []))
        mission_skills = [s for s in task.get("mission_skills", []) if s in enabled or s == "platform"]

        prompt = task.get("mission_prompt", "")
        if task.get("context_as_input") and task.get("last_result"):
            prompt += f"\n\n[Last execution result]\n{task['last_result']}"

        if self._app_service:
            result = await self._app_service.run_agent_mission(
                tenant=tenant,
                user_id=task["user_id"],
                channel=task["channel"],
                mission_prompt=prompt,
                allowed_skills=mission_skills,
            )
            return result or ""
        return "AppService not available"

    # ==========================================
    # Skill availability handling
    # ==========================================

    async def _handle_skill_disabled(self, task: dict, error: SkillNotAvailableError):
        action = task.get("skill_disabled_action", "notify_admin")
        logger.warning(f"Task {task['id']} skill unavailable: {error.skill}, action: {action}")

        if action == "notify_admin" and self._alerter:
            await self._alerter.send(
                level="warning",
                title="Scheduled task skill unavailable",
                detail=f"**Tenant**: {error.tenant_id}\n**Task**: {task['id']}\n**Skill**: {error.skill}",
            )
        elif action == "deactivate_task":
            async with async_session_factory() as session:
                repo = TaskRepository(session)
                await repo.deactivate(task["id"])
                await session.commit()
            self.cancel(task["id"])

    async def _get_tenant_and_check_skill(self, tenant_id: str, skill_name: str, task_id: str):
        async with async_session_factory() as session:
            tenant_repo = SQLAlchemyTenantRepository(session)
            tenant = await tenant_repo.get_by_id(tenant_id)
        if skill_name and skill_name != "platform":
            enabled = tenant.config.get("enabled_skills", [])
            if skill_name not in enabled:
                raise SkillNotAvailableError(skill_name, tenant_id, task_id)
        return tenant

    # ==========================================
    # API
    # ==========================================

    def list_jobs(self) -> list:
        jobs = self._scheduler.get_jobs()
        return [{"id": j.id, "next_run": str(j.next_run_time)} for j in jobs]

    @property
    def job_count(self) -> int:
        return len(self._scheduler.get_jobs())

    @property
    def is_running(self) -> bool:
        return self._scheduler.running
