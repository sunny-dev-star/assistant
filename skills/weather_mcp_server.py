#!/usr/bin/env python3
"""
示例 MCP Server - 天气查询
用于验证框架的 MCP 集成能力
"""
import json
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import Tool
from mcp.types import TextContent

app = Server("weather-mcp")


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="mcp_get_weather",
            description="通过 MCP 协议查询城市天气",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="mcp_get_forecast",
            description="通过 MCP 协议查询城市天气预报",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "days": {"type": "integer", "description": "预报天数(1-3)", "default": 3},
                },
                "required": ["city"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "mcp_get_weather":
        city = arguments["city"]
        try:
            r = httpx.get(f"https://wttr.in/{city}", params={"format": "j1", "lang": "zh"}, timeout=15)
            if r.status_code != 200:
                return [TextContent(type="text", text=json.dumps({"error": f"无法获取{city}的天气"}, ensure_ascii=False))]
            c = r.json().get("current_condition", [{}])[0]
            d = c.get("lang_zh", [{}])[0].get("value", c.get("weatherDesc", [{}])[0].get("value", "?"))
            return [TextContent(type="text", text=json.dumps({
                "城市": city, "天气": d, "温度": f"{c.get('temp_C','?')}°C",
                "体感温度": f"{c.get('FeelsLikeC','?')}°C", "湿度": f"{c.get('humidity','?')}%",
                "风速": f"{c.get('windspeedKmph','?')} km/h", "风向": c.get("winddir16Point","?"),
                "紫外线指数": c.get("uvIndex","?"),
            }, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]

    elif name == "mcp_get_forecast":
        city = arguments["city"]
        days = arguments.get("days", 3)
        try:
            r = httpx.get(f"https://wttr.in/{city}", params={"format": "j1", "lang": "zh"}, timeout=15)
            if r.status_code != 200:
                return [TextContent(type="text", text=json.dumps({"error": f"无法获取{city}的预报"}, ensure_ascii=False))]
            fs = []
            for day in r.json().get("weather", [])[:days]:
                h = day.get("hourly", [])
                desc = h[len(h)//2].get("lang_zh",[{}])[0].get("value","?") if h else "?"
                fs.append({"日期": day.get("date"), "天气": desc,
                           "最高温": f"{day.get('maxtempC')}°C", "最低温": f"{day.get('mintempC')}°C"})
            return [TextContent(type="text", text=json.dumps({"城市": city, "天气预报": fs}, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
