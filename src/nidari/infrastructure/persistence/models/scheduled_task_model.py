"""
Scheduled Task ORM models
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, JSON
from sqlalchemy.sql import func

from ..database import Base


class ScheduledTaskModel(Base):
    __tablename__ = "scheduled_tasks"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False)
    channel = Column(String(20), nullable=False, default="wechat")
    task_type = Column(String(50), nullable=False)
    display_name = Column(Text)

    cron_expr = Column(String(100))
    run_once_at = Column(DateTime)
    timezone = Column(String(50), default="Asia/Shanghai")

    execution_type = Column(String(20), nullable=False, default="message")
    message = Column(Text)
    skill_name = Column(String(50))
    tool_name = Column(String(50))
    tool_args = Column(JSON, default=dict)
    steps = Column(JSON, default=list)
    mission_prompt = Column(Text)
    mission_skills = Column(JSON, default=list)
    context_as_input = Column(Boolean, default=False)
    result_as_message = Column(Boolean, default=True)
    skill_disabled_action = Column(String(20), default="notify_admin")

    # 角色上下文 — 记录任务创建时的操作角色，触发时做权限校验
    role_name = Column(String(50))

    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime)
    last_result = Column(Text)
    run_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    next_run_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TaskExecutionLogModel(Base):
    __tablename__ = "task_execution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime)
    status = Column(String(20), nullable=False, default="running")
    result = Column(Text)
    error_detail = Column(Text)
    steps_log = Column(JSON, default=list)
