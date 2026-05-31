"""
Billing and usage report router
"""
from fastapi import APIRouter, Request, Query
from typing import Optional

from ....app.services.billing_service import BillingService
from ....infrastructure.persistence.database import async_session_factory

router = APIRouter()


@router.get("/tenants/{tenant_id}/billing")
async def get_tenant_billing(
    request: Request,
    tenant_id: str,
    year: int = Query(..., description="Year, e.g. 2026"),
    month: int = Query(..., ge=1, le=12, description="Month 1-12"),
):
    """Get monthly billing report for a tenant"""
    billing = BillingService(async_session_factory)
    record = await billing.generate_monthly_report(tenant_id, year, month)
    return {
        "tenant_id": record.tenant_id,
        "period": record.period,
        "total_conversations": record.total_conversations,
        "total_messages": record.total_messages,
        "total_tokens_input": record.total_tokens_input,
        "total_tokens_output": record.total_tokens_output,
        "total_tokens": record.total_tokens,
        "total_cost_usd": record.total_cost_usd,
        "by_model": record.by_model,
        "by_skill": record.by_skill,
        "by_channel": record.by_channel,
    }


@router.get("/tenants/{tenant_id}/billing/export")
async def export_tenant_billing(
    request: Request,
    tenant_id: str,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
):
    """Export billing report as CSV"""
    from starlette.responses import Response as StarletteResponse

    billing = BillingService(async_session_factory)
    record = await billing.generate_monthly_report(tenant_id, year, month)
    csv_content = await billing.export_report_csv(record)

    filename = f"billing_{tenant_id}_{year}{month:02d}.csv"
    return StarletteResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tenants/{tenant_id}/usage")
async def get_tenant_usage(
    request: Request,
    tenant_id: str,
    days: int = Query(7, ge=1, le=90, description="Last N days"),
):
    """Get recent usage stats for a tenant"""
    from sqlalchemy import text
    from datetime import datetime, timedelta

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    async with async_session_factory() as session:
        # Daily usage
        sql = text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as calls,
                COALESCE(SUM(total_tokens), 0) as tokens,
                COALESCE(SUM(cost_usd), 0) as cost_usd
            FROM api_usage
            WHERE tenant_id = :tenant_id
              AND created_at >= :since
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        result = await session.execute(sql, {"tenant_id": tenant_id, "since": since})
        daily = [
            {
                "date": str(row[0]),
                "calls": row[1],
                "tokens": row[2],
                "cost_usd": (row[3] or 0) / 1_000_000,
            }
            for row in result.fetchall()
        ]

        # Summary
        summary_sql = text("""
            SELECT
                COUNT(*) as total_calls,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as total_cost_usd
            FROM api_usage
            WHERE tenant_id = :tenant_id
              AND created_at >= :since
        """)
        result = await session.execute(summary_sql, {"tenant_id": tenant_id, "since": since})
        row = result.fetchone()

    return {
        "tenant_id": tenant_id,
        "days": days,
        "summary": {
            "total_calls": row[0] if row else 0,
            "total_tokens": row[1] if row else 0,
            "total_cost_usd": (row[2] or 0) / 1_000_000 if row and row[2] else 0.0,
        },
        "daily": daily,
    }
