"""
Outbound scheduler management API
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class DailyGreetingRequest(BaseModel):
    user_id: str
    channel: str = "wechat"
    hour: int = 8
    minute: int = 0
    greeting_template: Optional[str] = None


class MedicationReminderRequest(BaseModel):
    user_id: str
    channel: str = "wechat"
    hour: int = 9
    minute: int = 0
    medication_name: str = "药物"


class FamilyReportRequest(BaseModel):
    elder_user_id: str
    family_user_id: str
    channel: str = "wechat"
    hour: int = 20
    minute: int = 0


class RemoveJobRequest(BaseModel):
    job_id: str


@router.get("/outbound/jobs")
async def list_outbound_jobs(request: Request):
    """List all scheduled outbound jobs"""
    scheduler = request.app.state.outbound_scheduler
    return {"jobs": scheduler.list_jobs(), "total": scheduler.job_count}


@router.post("/outbound/daily-greeting")
async def register_daily_greeting(request: Request, body: DailyGreetingRequest):
    """Register a daily morning greeting for an elder user"""
    tenant = request.state.tenant
    scheduler = request.app.state.outbound_scheduler
    job_id = f"greeting_{tenant.id}_{body.user_id}"

    scheduler.register_daily_greeting(
        job_id=job_id,
        tenant_id=tenant.id,
        user_id=body.user_id,
        channel=body.channel,
        hour=body.hour,
        minute=body.minute,
        greeting_template=body.greeting_template,
    )
    return {"status": "ok", "job_id": job_id, "message": f"Daily greeting registered at {body.hour}:{body.minute:02d}"}


@router.post("/outbound/medication-reminder")
async def register_medication_reminder(request: Request, body: MedicationReminderRequest):
    """Register a medication reminder"""
    tenant = request.state.tenant
    scheduler = request.app.state.outbound_scheduler
    job_id = f"med_{tenant.id}_{body.user_id}_{body.hour}{body.minute:02d}"

    scheduler.register_medication_reminder(
        job_id=job_id,
        tenant_id=tenant.id,
        user_id=body.user_id,
        channel=body.channel,
        hour=body.hour,
        minute=body.minute,
        medication_name=body.medication_name,
    )
    return {"status": "ok", "job_id": job_id}


@router.post("/outbound/family-report")
async def register_family_report(request: Request, body: FamilyReportRequest):
    """Register a daily family health report"""
    tenant = request.state.tenant
    scheduler = request.app.state.outbound_scheduler
    job_id = f"report_{tenant.id}_{body.family_user_id}"

    scheduler.register_family_report(
        job_id=job_id,
        tenant_id=tenant.id,
        user_id=body.elder_user_id,
        family_user_id=body.family_user_id,
        channel=body.channel,
        hour=body.hour,
        minute=body.minute,
    )
    return {"status": "ok", "job_id": job_id}


@router.delete("/outbound/jobs/{job_id}")
async def remove_outbound_job(request: Request, job_id: str):
    """Remove a scheduled job"""
    scheduler = request.app.state.outbound_scheduler
    scheduler.remove_job(job_id)
    return {"status": "ok", "removed": job_id}
