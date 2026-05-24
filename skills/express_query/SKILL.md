---
name: express-query
description: "Express tracking: query parcel status by tracking number. Auto-detects carrier (SF, JD, YT, ZTO, STO, YD, EMS). Use when user asks about package tracking, delivery status, where a parcel is, or provides a tracking number."
tools: [{"name": "query_express", "description": "Query logistics by tracking number", "parameters": {"type": "object", "properties": {"tracking_number": {"type": "string", "description": "Tracking number"}}, "required": ["tracking_number"]}}, {"name": "list_carriers", "description": "List supported carriers", "parameters": {"type": "object", "properties": {}}}]
---

# Express Query

## Tools

### query_express(tracking_number)
Run: `python3 scripts/track_express.py --tracking-number {tracking_number}`

### list_carriers()
Run: `python3 scripts/track_express.py --action list-carriers`

## Supported Carriers

| Prefix | Carrier |
|--------|---------|
| SF | 顺丰速运 |
| JD | 京东物流 |
| YT | 圆通速递 |
| ZTO | 中通快递 |
| STO | 申通快递 |
| YD | 韵达快递 |
| EMS | EMS |

## References
- [Carrier identification rules](references/carrier-rules.md)
