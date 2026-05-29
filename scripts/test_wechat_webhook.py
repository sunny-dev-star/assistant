#!/usr/bin/env python3
"""
Simulate WeChat Official Account webhook calls against a running Nidari instance.

Usage:
  export WECHAT_TOKEN="your_token"
  export TENANT_ID="tnt_wechat_demo"
  export BASE_URL="http://localhost:8000"

  python3 scripts/test_wechat_webhook.py verify
  python3 scripts/test_wechat_webhook.py message --text "你好"
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
import uuid

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    sys.exit(1)


def _sign(token: str, timestamp: str, nonce: str) -> str:
    raw = "".join(sorted([token, timestamp, nonce])).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def cmd_verify(base_url: str, tenant_id: str, token: str) -> int:
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex[:8]
    echostr = "nidari_echo_test"
    sig = _sign(token, ts, nonce)
    url = f"{base_url.rstrip('/')}/webhook/wechat/{tenant_id}"
    r = requests.get(
        url,
        params={"signature": sig, "timestamp": ts, "nonce": nonce, "echostr": echostr},
        timeout=10,
    )
    print(f"GET {url}")
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text}")
    if r.status_code == 200 and r.text == echostr:
        print("PASS: WeChat verify simulation succeeded")
        return 0
    print("FAIL: expected 200 with echostr body")
    return 1


def cmd_message(base_url: str, tenant_id: str, text: str, openid: str) -> int:
    xml = f"""<xml>
<ToUserName><![CDATA[gh_demo]]></ToUserName>
<FromUserName><![CDATA[{openid}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{text}]]></Content>
<MsgId>{int(time.time())}</MsgId>
</xml>"""
    url = f"{base_url.rstrip('/')}/webhook/wechat/{tenant_id}"
    r = requests.post(url, data=xml.encode("utf-8"), headers={"Content-Type": "text/xml"}, timeout=120)
    print(f"POST {url}")
    print(f"Status: {r.status_code}")
    print(f"Response XML:\n{r.text}")
    if r.status_code == 200 and "<Content>" in r.text:
        print("PASS: received XML reply")
        return 0
    print("FAIL: expected 200 with XML content reply")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Nidari WeChat webhook")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("verify", help="Simulate WeChat server URL verification (GET)")
    p_msg = sub.add_parser("message", help="Simulate inbound text message (POST)")
    p_msg.add_argument("--text", default="你好", help="Message text")
    p_msg.add_argument("--openid", default="oDemoUserOpenId001", help="Simulated WeChat OpenID")

    args = parser.parse_args()
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    tenant_id = os.getenv("TENANT_ID", "tnt_wechat_demo")
    token = os.getenv("WECHAT_TOKEN", "")

    if args.command == "verify":
        if not token:
            print("ERROR: WECHAT_TOKEN required for verify", file=sys.stderr)
            return 1
        return cmd_verify(base_url, tenant_id, token)

    if args.command == "message":
        return cmd_message(base_url, tenant_id, args.text, args.openid)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
