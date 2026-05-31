"""
Feishu (Lark) alerting via webhook
Sends interactive card messages to Feishu group for monitoring alerts
"""
import logging
from enum import Enum
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    EMERGENCY = "🚨 紧急"
    WARNING = "⚠️ 警告"
    INFO = "ℹ️ 通知"


# Card header color mapping
LEVEL_COLORS = {
    AlertLevel.EMERGENCY: "red",
    AlertLevel.WARNING: "yellow",
    AlertLevel.INFO: "blue",
}


class FeishuAlerter:
    """Send alerts to Feishu group via webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(
        self,
        level: AlertLevel,
        title: str,
        detail: str,
        mention_all: bool = False,
    ) -> bool:
        """
        Send an alert card to Feishu.

        Returns True if sent successfully, False otherwise.
        """
        if not self.webhook_url:
            logger.warning("Feishu webhook URL not configured, skipping alert")
            return False

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "content": f"{level.value} {title}",
                        "tag": "plain_text",
                    },
                    "template": LEVEL_COLORS.get(level, "blue"),
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"content": detail, "tag": "lark_md"},
                    }
                ],
            },
        }

        if mention_all:
            payload["card"]["elements"].append({
                "tag": "div",
                "text": {"content": "<at user_id='all'>所有人</at>", "tag": "lark_md"},
            })

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self.webhook_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 0:
                        logger.info(f"Feishu alert sent: {title}")
                        return True
                    else:
                        logger.error(f"Feishu alert failed: {data}")
                        return False
                else:
                    logger.error(f"Feishu webhook HTTP error: {resp.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Feishu alert exception: {e}")
            return False

    async def send_high_latency_alert(self, tenant_id: str, latency: float, threshold: float = 3.0):
        """Alert when response latency exceeds threshold"""
        await self.send(
            level=AlertLevel.WARNING,
            title="响应延迟过高",
            detail=f"**租户**: `{tenant_id}`\n**当前延迟**: {latency:.2f}s\n**阈值**: {threshold:.1f}s\n\n请检查 LLM 服务状态。",
        )

    async def send_error_rate_alert(self, error_rate: float, threshold: float = 0.05):
        """Alert when error rate exceeds threshold"""
        await self.send(
            level=AlertLevel.EMERGENCY,
            title="错误率过高",
            detail=f"**当前错误率**: {error_rate:.1%}\n**阈值**: {threshold:.0%}\n\n请立即检查服务状态！",
            mention_all=True,
        )

    async def send_quota_warning(self, tenant_id: str, usage_ratio: float):
        """Alert when tenant quota usage exceeds 85%"""
        await self.send(
            level=AlertLevel.WARNING,
            title="租户配额即将用尽",
            detail=f"**租户**: `{tenant_id}`\n**已用配额**: {usage_ratio:.1%}\n\n请提醒租户充值或升级套餐。",
        )

    async def send_daily_summary(self, total_chats: int, total_tokens: int, total_cost: float, error_count: int):
        """Send daily summary"""
        await self.send(
            level=AlertLevel.INFO,
            title="每日运营摘要",
            detail=(
                f"**今日对话**: {total_chats} 次\n"
                f"**Token 消耗**: {total_tokens:,}\n"
                f"**LLM 费用**: ${total_cost:.4f}\n"
                f"**错误次数**: {error_count}"
            ),
        )
