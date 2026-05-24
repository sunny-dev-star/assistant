#!/usr/bin/env python3
"""get_weather tool - query current weather or forecast

Usage:
  python3 get_weather.py --city 北京
  python3 get_weather.py --city 上海 --action forecast --days 3
"""
import httpx, json, argparse, sys


def get_weather(city: str) -> str:
    try:
        r = httpx.get(f"https://wttr.in/{city}", params={"format": "j1", "lang": "zh"}, timeout=15)
        if r.status_code != 200:
            return json.dumps({"error": f"无法获取{city}的天气"}, ensure_ascii=False)
        c = r.json().get("current_condition", [{}])[0]
        d = c.get("lang_zh", [{}])[0].get("value", c.get("weatherDesc", [{}])[0].get("value", "未知"))
        return json.dumps({"城市": city, "天气": d, "温度": f"{c.get('temp_C','?')}°C",
            "体感温度": f"{c.get('FeelsLikeC','?')}°C", "湿度": f"{c.get('humidity','?')}%",
            "风速": f"{c.get('windspeedKmph','?')} km/h", "风向": c.get("winddir16Point","?"),
            "能见度": f"{c.get('visibility','?')} km", "紫外线指数": c.get("uvIndex","?")}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def get_forecast(city: str, days: int = 3) -> str:
    try:
        r = httpx.get(f"https://wttr.in/{city}", params={"format": "j1", "lang": "zh"}, timeout=15)
        if r.status_code != 200:
            return json.dumps({"error": f"无法获取{city}的预报"}, ensure_ascii=False)
        fs = []
        for day in r.json().get("weather", [])[:days]:
            h = day.get("hourly", [])
            desc = h[len(h)//2].get("lang_zh",[{}])[0].get("value","?") if h else "?"
            fs.append({"日期": day.get("date"), "天气": desc, "最高温": f"{day.get('maxtempC')}°C",
                       "最低温": f"{day.get('mintempC')}°C", "平均温度": f"{day.get('avgtempC')}°C"})
        return json.dumps({"城市": city, "天气预报": fs}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--action", choices=["weather", "forecast"], default="weather")
    p.add_argument("--city", required=True)
    p.add_argument("--days", type=int, default=3)
    a = p.parse_args()
    print(get_forecast(a.city, a.days) if a.action == "forecast" else get_weather(a.city))
