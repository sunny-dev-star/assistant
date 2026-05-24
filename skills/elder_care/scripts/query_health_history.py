#!/usr/bin/env python3
"""
Query elder health data history
Usage: python3 query_health_history.py --user-id <id> [--data-type <type>] [--days 7]
"""
import argparse
import json
import os
from datetime import datetime, timedelta


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge", "health_records")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--data-type", default="all",
                       choices=["blood_pressure", "blood_glucose", "temperature", "weight", "heart_rate", "all"])
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    user_file = os.path.join(DATA_DIR, f"{args.user_id}.json")
    if not os.path.exists(user_file):
        print(json.dumps({"status": "ok", "records": [], "message": "暂无健康数据记录"}, ensure_ascii=False))
        return

    with open(user_file, "r") as f:
        records = json.load(f)

    # Filter by date range
    cutoff = (datetime.now() - timedelta(days=args.days)).isoformat()
    filtered = [r for r in records if r.get("recorded_at", "") >= cutoff]

    # Filter by data type
    if args.data_type != "all":
        filtered = [r for r in filtered if r.get("data_type") == args.data_type]

    result = {
        "status": "ok",
        "count": len(filtered),
        "days": args.days,
        "data_type": args.data_type,
        "records": filtered[-20:],  # Last 20 records max
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
