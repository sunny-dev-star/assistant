#!/usr/bin/env python3
"""List user's active scheduled tasks"""
import argparse
import json
import os

try:
    import httpx
except ImportError:
    import urllib.request
    httpx = None

PORT = os.getenv("PORT", "8000")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user_id", required=True)
    parser.add_argument("--tenant_id", required=True)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    try:
        if httpx:
            resp = httpx.get(
                f"http://localhost:{PORT}/internal/tasks",
                params={"user_id": args.user_id, "tenant_id": args.tenant_id, "limit": args.limit},
                timeout=5.0
            )
            data = resp.json()
        else:
            url = f"http://localhost:{PORT}/internal/tasks?user_id={args.user_id}&tenant_id={args.tenant_id}&limit={args.limit}"
            resp = urllib.request.urlopen(url, timeout=5)
            data = json.loads(resp.read())

        tasks = data.get("tasks", [])
        if not tasks:
            print(json.dumps({"tasks": [], "summary": "No active scheduled tasks"}, ensure_ascii=False))
            return

        items = []
        for t in tasks:
            freq = t.get("cron_expr") or f"once {str(t.get('run_once_at', ''))[:16]}"
            items.append({
                "task_id": t["id"],
                "name": t.get("display_name", t["task_type"]),
                "type": t["execution_type"],
                "schedule": freq,
                "last_run": str(t.get("last_run_at") or "never")[:16],
                "run_count": t.get("run_count", 0),
            })
        print(json.dumps({"tasks": items, "total": len(items)}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"tasks": [], "error": str(e)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
