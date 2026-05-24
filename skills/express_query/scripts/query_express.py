#!/usr/bin/env python3
"""query_express tool - track parcel

Usage: python3 query_express.py --tracking-number SF1234567890
"""
import json, random, argparse
from datetime import datetime, timedelta

CARRIERS = {"SF": "顺丰速运", "JD": "京东物流", "YT": "圆通速递", "ZTO": "中通快递", "STO": "申通快递", "YD": "韵达快递", "EMS": "EMS"}
STATUSES = ["已揽收", "运输中", "到达目的城市", "派送中", "已签收"]

def track(tn):
    carrier = "未知"
    for p, n in CARRIERS.items():
        if tn.upper().startswith(p):
            carrier = n; break
    idx = hash(tn) % 5
    status = STATUSES[idx]
    now = datetime.now()
    locs = ["北京市海淀区", "上海市浦东新区", "广州市天河区", "深圳市南山区", "杭州市西湖区"]
    evts = {"已揽收": "从 {} 揽收", "运输中": "到达【{}转运中心】", "到达目的城市": "到达【{}配送站】", "派送中": "快递员配送中", "已签收": "已签收"}
    tl = []
    for i in range(idx + 1):
        t = now - timedelta(hours=(idx-i)*8 + random.randint(0,4))
        tl.append({"时间": t.strftime("%Y-%m-%d %H:%M"), "状态": STATUSES[i],
                    "详情": evts.get(STATUSES[i], "").format(random.choice(locs))})
    return json.dumps({"单号": tn, "快递公司": carrier, "当前状态": status, "物流轨迹": list(reversed(tl))}, ensure_ascii=False)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--tracking-number", required=True)
    print(track(p.parse_args().tracking_number))
