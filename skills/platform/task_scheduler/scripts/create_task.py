#!/usr/bin/env python3
"""Create a scheduled task"""
import argparse
import json
import uuid
import os
from datetime import datetime

try:
    import httpx
except ImportError:
    import urllib.request
    httpx = None


PORT = os.getenv("PORT", "8000")


def parse_schedule(schedule: str) -> dict:
    s = schedule.strip()
    if s.startswith("cron:"):
        return {"type": "cron", "cron_expr": s[5:].strip()}
    if s.startswith("once:"):
        raw = s[5:].strip()
        try:
            dt = datetime.fromisoformat(raw)
            if dt <= datetime.now():
                return {"type": "error", "msg": "Specified time has passed"}
            return {"type": "once", "run_at": dt.isoformat()}
        except ValueError:
            return {"type": "error", "msg": f"Invalid time format: {raw}"}
    return {"type": "error", "msg": f"Expected cron:... or once:..., got: {s}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task_type", required=True)
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--execution_type", default="message")
    parser.add_argument("--display_name", default="")
    parser.add_argument("--message", default="")
    parser.add_argument("--skill_name", default="")
    parser.add_argument("--tool_name", default="")
    parser.add_argument("--tool_args", default="{}")
    parser.add_argument("--steps", default="[]")
    parser.add_argument("--mission_prompt", default="")
    parser.add_argument("--mission_skills", default="[]")
    parser.add_argument("--context_as_input", default="false")
    parser.add_argument("--skill_disabled_action", default="notify_admin")
    parser.add_argument("--user_id", required=True)
    parser.add_argument("--tenant_id", required=True)
    parser.add_argument("--channel", default="wechat")
    args = parser.parse_args()

    parsed = parse_schedule(args.schedule)
    if parsed["type"] == "error":
        print(json.dumps({"success": False, "error": parsed["msg"]}, ensure_ascii=False))
        return

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": task_id,
        "tenant_id": args.tenant_id,
        "user_id": args.user_id,
        "channel": args.channel,
        "task_type": args.task_type,
        "display_name": args.display_name or args.task_type,
        "execution_type": args.execution_type,
        "cron_expr": parsed.get("cron_expr"),
        "run_once_at": parsed.get("run_at"),
        "message": args.message,
        "skill_name": args.skill_name,
        "tool_name": args.tool_name,
        "tool_args": json.loads(args.tool_args),
        "steps": json.loads(args.steps),
        "mission_prompt": args.mission_prompt,
        "mission_skills": json.loads(args.mission_skills),
        "context_as_input": args.context_as_input.lower() == "true",
        "skill_disabled_action": args.skill_disabled_action,
    }

    try:
        if httpx:
            resp = httpx.post(
                f"http://localhost:{PORT}/internal/tasks",
                json=payload, timeout=5.0
            )
        else:
            req = urllib.request.Request(
                f"http://localhost:{PORT}/internal/tasks",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=5)

        freq = (
            f"cron `{parsed['cron_expr']}` recurring"
            if parsed["type"] == "cron"
            else f"once at {parsed['run_at']}"
        )
        print(json.dumps({
            "success": True,
            "task_id": task_id,
            "display_name": payload["display_name"],
            "frequency": freq,
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
