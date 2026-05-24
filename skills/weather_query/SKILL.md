---
name: weather-query
description: "Weather query: get current weather and forecasts for any city. Use when user asks about weather, temperature, rain, sunshine, what to wear, travel weather, UV index, or humidity for any city."
tools: [{"name": "get_weather", "description": "Query current weather for a city", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "City name"}}, "required": ["city"]}}, {"name": "get_forecast", "description": "Query weather forecast (1-3 days)", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "City name"}, "days": {"type": "integer", "description": "Forecast days (1-3)", "default": 3}}, "required": ["city"]}}]
---

# Weather Query

## Tools

### get_weather(city)
Run: `python3 scripts/get_weather.py --city {city}`

### get_forecast(city, days)
Run: `python3 scripts/get_weather.py --action forecast --city {city} --days {days}`

## References
- [Weather field definitions](references/weather-fields.md)
- [Dress advice rules](references/dress-advice.md)
