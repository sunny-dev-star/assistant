#!/usr/bin/env python3
"""
Trigger emergency alert for elder care
Usage: python3 trigger_emergency_alert.py --user-id <id> --situation <desc>
"""
import argparse
import json
import os
from datetime import datetime


ALERT_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge", "alerts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--situation", required=True)
    args = parser.parse_args()

    os.makedirs(ALERT_DIR, exist_ok=True)

    alert = {
        "user_id": args.user_id,
        "situation": args.situation,
        "severity": "urgent",
        "triggered_at": datetime.now().isoformat(),
        "status": "pending",
        "notified": False,
    }

    # Save alert
    alert_file = os.path.join(ALERT_DIR, f"{args.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(alert_file, "w") as f:
        json.dump(alert, f, ensure_ascii=False, indent=2)

    result = {
        "status": "alert_triggered",
        "alert_id": alert_file,
        "message": f"紧急警报已触发：{args.situation}",
        "actions_taken": [
            "已记录紧急事件",
            "待通知家属/社区工作人员",
            "建议立即拨打120",
        ],
        "timestamp": alert["triggered_at"],
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
