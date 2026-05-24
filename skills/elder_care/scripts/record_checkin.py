#!/usr/bin/env python3
"""
Record daily check-in (mood + note)
Usage: python3 record_checkin.py --user-id <id> --mood <好|一般|不好> [--note <note>]
"""
import argparse
import json
import os
from datetime import datetime


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge", "checkins")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--mood", required=True, choices=["好", "一般", "不好"])
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    checkin = {
        "user_id": args.user_id,
        "mood": args.mood,
        "note": args.note,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
    }

    # Append to checkin file
    user_file = os.path.join(DATA_DIR, f"{args.user_id}.json")
    checkins = []
    if os.path.exists(user_file):
        with open(user_file, "r") as f:
            checkins = json.load(f)
    checkins.append(checkin)
    with open(user_file, "w") as f:
        json.dump(checkins, f, ensure_ascii=False, indent=2)

    mood_responses = {
        "好": "很高兴您今天心情不错！继续保持好心情哦～",
        "一般": "嗯，一般的天气也有一般的风景嘛。有什么想聊的吗？",
        "不好": "听到您心情不太好，我陪您聊聊吧。有什么烦心事可以说出来，会好受一些的。",
    }

    result = {
        "status": "ok",
        "recorded": True,
        "mood": args.mood,
        "response": mood_responses.get(args.mood, ""),
        "date": checkin["date"],
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
