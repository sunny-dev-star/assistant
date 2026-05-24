#!/usr/bin/env python3
"""get_forecast tool - weather forecast (wrapper)

Usage: python3 get_forecast.py --city 北京 --days 3
"""
import sys
# 复用 get_weather.py 的逻辑
sys.argv = [sys.argv[0], "--action", "forecast"] + sys.argv[1:]
exec(open(__file__).read().replace("get_forecast.py", "get_weather.py").split("if __name__")[0])
# 但更简单的方式：
import subprocess, argparse
p = argparse.ArgumentParser()
p.add_argument("--city", required=True)
p.add_argument("--days", type=int, default=3)
a = p.parse_args()
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
r = subprocess.run(["python3", f"{script_dir}/get_weather.py", "--action", "forecast", "--city", a.city, "--days", str(a.days)],
                   capture_output=True, text=True)
print(r.stdout.strip())
