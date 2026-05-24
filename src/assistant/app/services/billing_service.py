"""
API usage billing service
Generates monthly usage reports per tenant, with model/skill breakdown
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Usage record for a period"""
    tenant_id: str
    period: str  # "YYYY-MM"
    total_conversations: int = 0
    total_messages: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_skill: Dict[str, int] = field(default_factory=dict)
    by_channel: Dict[str, int] = field(default_factory=dict)


class BillingService:
    """Generate monthly usage reports for tenants"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def generate_monthly_report(
        self,
        tenant_id: str,
        year: int,
        month: int
    ) -> UsageRecord:
        """Generate monthly usage report for a tenant"""
        from sqlalchemy import text
        period = f"{year}-{month:02d}"
        period_start = f"{year}-{month:02d}-01"
        # Calculate period end (first day of next month)
        if month == 12:
            period_end = f"{year+1}-01-01"
        else:
            period_end = f"{year}-{month+1:02d}-01"

        async with self.session_factory() as session:
            # 1. Overall usage from api_usage table
            usage_sql = text("""
                SELECT
                    COUNT(*) as total_calls,
                    COALESCE(SUM(prompt_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(completion_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(cost_usd), 0) as total_cost_usd
                FROM api_usage
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
            """)
            result = await session.execute(usage_sql, {
                "tenant_id": tenant_id,
                "period_start": period_start,
                "period_end": period_end,
            })
            row = result.fetchone()

            record = UsageRecord(
                tenant_id=tenant_id,
                period=period,
                total_conversations=row[0] if row else 0,
                total_tokens_input=row[1] if row else 0,
                total_tokens_output=row[2] if row else 0,
                total_tokens=row[3] if row else 0,
                total_cost_usd=(row[4] or 0) / 1_000_000 if row else 0.0,  # micro-dollars to dollars
            )

            # 2. Breakdown by model
            model_sql = text("""
                SELECT
                    model,
                    COUNT(*) as calls,
                    COALESCE(SUM(total_tokens), 0) as tokens,
                    COALESCE(SUM(cost_usd), 0) as cost_usd
                FROM api_usage
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                GROUP BY model
            """)
            result = await session.execute(model_sql, {
                "tenant_id": tenant_id,
                "period_start": period_start,
                "period_end": period_end,
            })
            for row in result.fetchall():
                record.by_model[row[0]] = {
                    "calls": row[1],
                    "tokens": row[2],
                    "cost_usd": (row[3] or 0) / 1_000_000,
                }

            # 3. Breakdown by skill
            skill_sql = text("""
                SELECT
                    COALESCE(skill_name, 'none') as skill,
                    COUNT(*) as calls
                FROM api_usage
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                GROUP BY skill_name
            """)
            result = await session.execute(skill_sql, {
                "tenant_id": tenant_id,
                "period_start": period_start,
                "period_end": period_end,
            })
            for row in result.fetchall():
                record.by_skill[row[0]] = row[1]

            # 4. Breakdown by channel
            channel_sql = text("""
                SELECT
                    COALESCE(channel, 'unknown') as channel,
                    COUNT(*) as calls
                FROM api_usage
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                GROUP BY channel
            """)
            result = await session.execute(channel_sql, {
                "tenant_id": tenant_id,
                "period_start": period_start,
                "period_end": period_end,
            })
            for row in result.fetchall():
                record.by_channel[row[0]] = row[1]

            # 5. Conversation count (distinct)
            conv_sql = text("""
                SELECT COUNT(DISTINCT conversation_id)
                FROM api_usage
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
            """)
            result = await session.execute(conv_sql, {
                "tenant_id": tenant_id,
                "period_start": period_start,
                "period_end": period_end,
            })
            record.total_conversations = result.scalar() or 0

            # 6. Message count
            msg_sql = text("""
                SELECT COUNT(*)
                FROM messages
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
            """)
            result = await session.execute(msg_sql, {
                "tenant_id": tenant_id,
                "period_start": period_start,
                "period_end": period_end,
            })
            record.total_messages = result.scalar() or 0

        return record

    async def export_report_csv(self, record: UsageRecord) -> str:
        """Export report as CSV string"""
        lines = [
            "tenant_id,period,conversations,messages,tokens_input,tokens_output,total_tokens,cost_usd",
            f"{record.tenant_id},{record.period},{record.total_conversations},{record.total_messages},"
            f"{record.total_tokens_input},{record.total_tokens_output},{record.total_tokens},"
            f"{record.total_cost_usd:.6f}",
            "",
            "# Model Breakdown",
            "model,calls,tokens,cost_usd",
        ]
        for model, data in record.by_model.items():
            lines.append(f"{model},{data['calls']},{data['tokens']},{data['cost_usd']:.6f}")

        lines.append("")
        lines.append("# Skill Breakdown")
        lines.append("skill,calls")
        for skill, calls in record.by_skill.items():
            lines.append(f"{skill},{calls}")

        lines.append("")
        lines.append("# Channel Breakdown")
        lines.append("channel,calls")
        for channel, calls in record.by_channel.items():
            lines.append(f"{channel},{calls}")

        return "\n".join(lines)
