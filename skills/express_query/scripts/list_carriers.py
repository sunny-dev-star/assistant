#!/usr/bin/env python3
"""list_carriers tool - list supported express carriers

Usage: python3 list_carriers.py
"""
import json
CARRIERS = {"SF": "顺丰速运", "JD": "京东物流", "YT": "圆通速递", "ZTO": "中通快递", "STO": "申通快递", "YD": "韵达快递", "EMS": "EMS"}
if __name__ == "__main__":
    print(json.dumps({"快递公司": [{"代码": k, "名称": v} for k, v in CARRIERS.items()]}, ensure_ascii=False))
