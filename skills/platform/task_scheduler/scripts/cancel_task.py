#!/usr/bin/env python3
"""Cancel a scheduled task"""
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
    parser.add_argument("--task_id", required=True)
    parser.add_argument("--user_id", required=True)
    parser.add_argument("--tenant_id", required=True)
    args = parser.parse_args()

    try:
        if httpx:
            resp = httpx.delete(
                f"http://localhost:{PORT}/internal/tasks/{args.task_id}",
                params={"user_id": args.user_id, "tenant_id": args.tenant_id},
                timeout=5.0
            )
            status = resp.status_code
        else:
            url = f"http://localhost:{PORT}/internal/tasks/{args.task_id}?user_id={args.user_id}&tenant_id={args.tenant_id}"
            req = urllib.request.Request(url, method="DELETE")
            resp = urllib.request.urlopen(req, timeout=5)
            status = 200

        if status == 200:
            print(json.dumps({"success": True, "message": f"Task {args.task_id} cancelled"}, ensure_ascii=False))
        elif status == 403:
            print(json.dumps({"success": False, "error": "No permission to cancel this task"}, ensure_ascii=False))
        else:
            print(json.dumps({"success": False, "error": "Cancel failed"}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
