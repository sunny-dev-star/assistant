#!/usr/bin/env python3
"""
Record elder health data (blood pressure, blood glucose, etc.)
Usage: python3 log_health_data.py --user-id <id> --data-type <type> --value <val> [--note <note>]
"""
import argparse
import json
import os
from datetime import datetime


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge", "health_records")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--data-type", required=True,
                       choices=["blood_pressure", "blood_glucose", "temperature", "weight", "heart_rate"])
    parser.add_argument("--value", required=True)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    record = {
        "user_id": args.user_id,
        "data_type": args.data_type,
        "value": args.value,
        "note": args.note,
        "recorded_at": datetime.now().isoformat(),
    }

    # Append to user's health file
    user_file = os.path.join(DATA_DIR, f"{args.user_id}.json")
    records = []
    if os.path.exists(user_file):
        with open(user_file, "r") as f:
            records = json.load(f)
    records.append(record)
    with open(user_file, "w") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # Check for anomalies
    warnings = check_anomaly(args.data_type, args.value)

    result = {
        "status": "ok",
        "recorded": True,
        "data_type": args.data_type,
        "value": args.value,
        "timestamp": record["recorded_at"],
    }
    if warnings:
        result["warnings"] = warnings

    print(json.dumps(result, ensure_ascii=False))


def check_anomaly(data_type: str, value: str) -> list:
    """Check if health data is abnormal"""
    warnings = []
    try:
        if data_type == "blood_pressure":
            parts = value.split("/")
            if len(parts) == 2:
                systolic = int(parts[0])
                diastolic = int(parts[1])
                if systolic > 160:
                    warnings.append("收缩压偏高(>160)，建议尽快就医")
                elif systolic < 90:
                    warnings.append("收缩压偏低(<90)，建议就医检查")
                if diastolic > 100:
                    warnings.append("舒张压偏高(>100)，建议就医")
        elif data_type == "blood_glucose":
            val = float(value)
            if val > 7.0:
                warnings.append("空腹血糖偏高(>7.0mmol/L)，建议复查")
            elif val < 3.9:
                warnings.append("血糖偏低(<3.9mmol/L)，建议补充糖分")
        elif data_type == "temperature":
            val = float(value)
            if val > 38.5:
                warnings.append("体温偏高(>38.5°C)，建议就医")
        elif data_type == "heart_rate":
            val = int(value)
            if val > 100:
                warnings.append("心率偏快(>100)，请关注")
            elif val < 50:
                warnings.append("心率偏慢(<50)，请关注")
    except (ValueError, IndexError):
        pass
    return warnings


if __name__ == "__main__":
    main()
