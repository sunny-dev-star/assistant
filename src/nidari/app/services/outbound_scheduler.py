"""
Proactive outbound scheduler
Schedules recurring tasks: daily greetings, health reminders, family reports.
Uses APScheduler for cron-like scheduling within the agent-engine process.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class OutboundScheduler:
    """
    Manages proactive outbound messages (daily greetings, health reminders, etc).
    Integrates with the ConversationAppService for message delivery.
    """

    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self._app_service = None
        self._channel_adapters: Dict[str, Any] = {}
        self._jobs: Dict[str, Any] = {}

    def configure(self, app_service=None, channel_adapters: Dict[str, Any] = None):
        """Inject dependencies"""
        self._app_service = app_service
        if channel_adapters:
            self._channel_adapters.update(channel_adapters)

    def start(self):
        """Start the scheduler"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("OutboundScheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("OutboundScheduler stopped")

    # =============================================
    # Job Registration
    # =============================================

    def register_daily_greeting(
        self,
        job_id: str,
        tenant_id: str,
        user_id: str,
        channel: str,
        hour: int = 8,
        minute: int = 0,
        greeting_template: str = None,
    ):
        """
        Register a daily morning greeting for an elder user.
        Default: 8:00 AM every day.
        """
        template = greeting_template or "早上好呀！今天感觉怎么样？有没有按时吃早饭呀？"

        async def _send_greeting():
            await self._send_proactive(
                tenant_id=tenant_id,
                user_id=user_id,
                channel=channel,
                message=template,
                skill="elder_care",
                metadata={"job_type": "daily_greeting"},
            )

        job = self._scheduler.add_job(
            _send_greeting,
            CronTrigger(hour=hour, minute=minute),
            id=job_id,
            name=f"Daily greeting for {user_id}",
            replace_existing=True,
        )
        self._jobs[job_id] = job
        logger.info(f"Registered daily greeting: {job_id} at {hour}:{minute:02d} for user {user_id}")

    def register_medication_reminder(
        self,
        job_id: str,
        tenant_id: str,
        user_id: str,
        channel: str,
        hour: int,
        minute: int = 0,
        medication_name: str = "药物",
    ):
        """Register a medication reminder at specific time"""
        message = f"该吃药啦💊！记得服用{medication_name}，吃完记得告诉我哦～"

        async def _send_reminder():
            await self._send_proactive(
                tenant_id=tenant_id,
                user_id=user_id,
                channel=channel,
                message=message,
                skill="elder_care",
                metadata={"job_type": "medication_reminder", "medication": medication_name},
            )

        job = self._scheduler.add_job(
            _send_reminder,
            CronTrigger(hour=hour, minute=minute),
            id=job_id,
            name=f"Medication reminder for {user_id} at {hour}:{minute:02d}",
            replace_existing=True,
        )
        self._jobs[job_id] = job
        logger.info(f"Registered medication reminder: {job_id} at {hour}:{minute:02d}")

    def register_family_report(
        self,
        job_id: str,
        tenant_id: str,
        user_id: str,  # elder's user_id
        family_user_id: str,  # family member's user_id
        channel: str,
        hour: int = 20,
        minute: int = 0,
    ):
        """
        Register a daily family report sent to the family member.
        Default: 8:00 PM every day.
        """
        async def _send_report():
            # Query elder's health data and checkins for today
            report = await self._generate_daily_report(tenant_id, user_id)
            await self._send_proactive(
                tenant_id=tenant_id,
                user_id=family_user_id,
                channel=channel,
                message=report,
                skill="elder_care",
                metadata={"job_type": "family_report", "elder_user_id": user_id},
            )

        job = self._scheduler.add_job(
            _send_report,
            CronTrigger(hour=hour, minute=minute),
            id=job_id,
            name=f"Family report for {family_user_id} about {user_id}",
            replace_existing=True,
        )
        self._jobs[job_id] = job
        logger.info(f"Registered family report: {job_id} at {hour}:{minute:02d}")

    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        if job_id in self._jobs:
            self._scheduler.remove_job(job_id)
            del self._jobs[job_id]
            logger.info(f"Removed job: {job_id}")

    # =============================================
    # Execution
    # =============================================

    async def _send_proactive(
        self,
        tenant_id: str,
        user_id: str,
        channel: str,
        message: str,
        skill: str = None,
        metadata: dict = None,
    ):
        """Send a proactive message through the channel adapter"""
        from ..domain.models.context import TenantContext, LLMConfig
        from ..domain.value_objects.channel import Channel
        from ..infrastructure.config.settings import settings

        logger.info(f"Sending proactive message to {user_id} via {channel}: {message[:50]}...")

        try:
            # Build context (using system identity, no tenant auth needed for outbound)
            llm_config = LLMConfig(
                provider="openai_compat",
                model=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY or None,
            )
            context = TenantContext(
                tenant_id=tenant_id,
                user_id=user_id,
                channel=Channel(channel),
                session_id=f"proactive_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                llm_config=llm_config,
                allowed_skills=[skill] if skill else [],
                metadata=metadata or {},
            )

            # If we have a channel adapter, use its proactive send
            adapter = self._channel_adapters.get(channel)
            if adapter:
                from ..domain.ports.channel_port import OutboundMessage
                outbound = OutboundMessage(content=message)
                await adapter.send_proactive(user_id, outbound)
            else:
                # Fallback: log it (in production this goes through the channel)
                logger.info(f"[Proactive] channel={channel} user={user_id}: {message}")

            # Also record in conversation history via AppService if available
            if self._app_service:
                await self._app_service.execute(
                    context=context,
                    user_message_content=f"[系统主动发送] {message}",
                )

        except Exception as e:
            logger.error(f"Proactive message failed: {e}", exc_info=True)

    async def _generate_daily_report(self, tenant_id: str, elder_user_id: str) -> str:
        """Generate a daily summary for family member"""
        import os
        import json

        # Read health records
        health_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "skills", "elder_care", "knowledge", "health_records"
        )
        checkin_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "skills", "elder_care", "knowledge", "checkins"
        )

        report_lines = [f"📋 **今日健康日报**（{datetime.now().strftime('%Y-%m-%d')}）\n"]

        # Health data
        health_file = os.path.join(health_dir, f"{elder_user_id}.json")
        if os.path.exists(health_file):
            with open(health_file, "r") as f:
                records = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            today_records = [r for r in records if r.get("recorded_at", "").startswith(today)]
            if today_records:
                report_lines.append("**健康数据：**")
                for r in today_records:
                    dt = r.get("data_type", "")
                    val = r.get("value", "")
                    note = r.get("note", "")
                    warnings = r.get("warnings", [])
                    line = f"  - {dt}: {val}"
                    if note:
                        line += f" ({note})"
                    if warnings:
                        line += f" ⚠️ {'; '.join(warnings)}"
                    report_lines.append(line)
            else:
                report_lines.append("**健康数据：** 今日暂无记录")
        else:
            report_lines.append("**健康数据：** 暂无数据")

        # Checkin
        checkin_file = os.path.join(checkin_dir, f"{elder_user_id}.json")
        if os.path.exists(checkin_file):
            with open(checkin_file, "r") as f:
                checkins = json.load(f)
            today_checkins = [c for c in checkins if c.get("date") == datetime.now().strftime("%Y-%m-%d")]
            if today_checkins:
                c = today_checkins[-1]
                report_lines.append(f"\n**心情：** {c.get('mood', '未知')}")
                if c.get("note"):
                    report_lines.append(f"**备注：** {c['note']}")
            else:
                report_lines.append("\n**签到：** 今日未签到")

        report_lines.append("\n如有异常，系统会第一时间通知您。祝好！🌙")
        return "\n".join(report_lines)

    # =============================================
    # API
    # =============================================

    def list_jobs(self) -> list:
        """List all registered jobs"""
        result = []
        for job_id, job in self._jobs.items():
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
            result.append({
                "job_id": job_id,
                "name": job.name,
                "next_run": next_run,
            })
        return result

    @property
    def job_count(self) -> int:
        return len(self._jobs)

    @property
    def is_running(self) -> bool:
        return self._scheduler.running
