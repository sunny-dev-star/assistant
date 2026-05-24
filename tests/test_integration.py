#!/usr/bin/env python3
"""
Assistant Framework - Integration Test Suite
Usage: python3 tests/test_integration.py [BASE_URL] [AUTH_TOKEN]
"""
import sys
import json
import time

try:
    import requests
except ImportError:
    print("pip install requests first")
    sys.exit(1)

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
TOKEN = sys.argv[2] if len(sys.argv) > 2 else ""

PASS = 0
FAIL = 0


def p(name):
    global PASS
    PASS += 1
    print(f"  \033[92m[PASS]\033[0m {name}")


def f(name, detail=""):
    global FAIL
    FAIL += 1
    print(f"  \033[91m[FAIL]\033[0m {name}" + (f" — {detail}" if detail else ""))


def info(msg):
    print(f"  \033[93m[INFO]\033[0m {msg}")


def chat(message, user_id="u1", session_id=None):
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    payload = {"message": message, "user_id": user_id}
    if session_id:
        payload["session_id"] = session_id
    return requests.post(f"{BASE}/v1/chat", headers=headers, json=payload, timeout=60)


print("=" * 50)
print("  Assistant Integration Test Suite")
print(f"  Target: {BASE}")
print(f"  Auth:   {'ON (Bearer)' if TOKEN else 'OFF (dev mode)'}")
print("=" * 50)

# =============================================
print("\n--- 1. Health & Infrastructure ---")

r = requests.get(f"{BASE}/health", timeout=5)
if r.status_code == 200:
    p("Health check (200)")
else:
    f("Health check", f"got {r.status_code}")

r = requests.get(f"{BASE}/", timeout=5)
if r.status_code == 200 and "Assistant API" in r.text:
    p("Root endpoint")
else:
    f("Root endpoint", f"got {r.status_code}")

r = requests.get(f"{BASE}/metrics", timeout=5)
if r.status_code == 200 and "agent_chat_requests_total" in r.text:
    p("Prometheus metrics")
else:
    f("Prometheus metrics", f"got {r.status_code}")

r = requests.get(f"{BASE}/openapi.json", timeout=5)
if r.status_code == 200:
    paths = r.json().get("paths", {})
    p(f"OpenAPI spec ({len(paths)} endpoints)")
else:
    f("OpenAPI spec", f"got {r.status_code}")

# =============================================
print("\n--- 2. Skills ---")

r = requests.get(f"{BASE}/v1/skills", timeout=5)
data = r.json()
if data.get("total", 0) >= 3:
    p(f"Skills loaded: {data['total']} skills, {data.get('tools_total',0)} tools")
else:
    f("Skills", f"expected >=3, got {data.get('total',0)}")

r = requests.get(f"{BASE}/v1/skills/elder_care", timeout=5)
if r.status_code == 200:
    ec = r.json()
    tools = [t["name"] for t in ec.get("tools", [])]
    if len(tools) >= 4:
        p(f"Elder care: {len(tools)} tools ({', '.join(tools)})")
    else:
        f("Elder care tools", f"expected 4, got {len(tools)}")
else:
    f("Elder care detail", f"got {r.status_code}")

# =============================================
print("\n--- 3. Chat (Basic) ---")

r = chat("你好，我是小明")
if r.status_code == 200:
    data = r.json()
    reply = data.get("reply", "")
    sid = data.get("session_id", "")
    if reply:
        p("Basic chat reply received")
        info(f"Reply: {reply[:60]}...")
        info(f"Session: {sid}")
    else:
        f("Basic chat", "empty reply")
else:
    f("Basic chat", f"got {r.status_code}: {r.text[:100]}")

# Session continuity
if r.status_code == 200 and sid:
    time.sleep(1)
    r2 = chat("刚才我说了我叫什么名字？", user_id="u1", session_id=sid)
    if r2.status_code == 200:
        data2 = r2.json()
        if data2.get("session_id") == sid:
            p("Session continuity (same session_id)")
            info(f"Reply: {data2.get('reply', '')[:60]}...")
        else:
            f("Session continuity", f"expected {sid}, got {data2.get('session_id')}")
    else:
        f("Session follow-up", f"got {r2.status_code}")

# =============================================
print("\n--- 4. Chat (Tool Calling) ---")

time.sleep(1)
r = chat("今天成都天气怎么样？", user_id="u2")
if r.status_code == 200:
    reply = r.json().get("reply", "")
    if reply:
        p("Weather tool call")
        info(f"Reply: {reply[:80]}...")
    else:
        f("Weather tool", "empty reply")
else:
    f("Weather tool", f"got {r.status_code}")

# =============================================
print("\n--- 5. Auth Mode ---")

r = requests.post(f"{BASE}/v1/chat",
    json={"message": "test", "user_id": "u1"}, timeout=10)
if r.status_code == 401:
    p("No-token request rejected (auth ON)")
elif r.status_code == 200:
    info("Auth disabled (dev mode) — 200 without token")
else:
    f("Auth check", f"unexpected {r.status_code}")

r = requests.post(f"{BASE}/v1/chat",
    headers={"Authorization": "Bearer ak_invalid_key"},
    json={"message": "test", "user_id": "u1"}, timeout=10)
if r.status_code == 401:
    p("Invalid token rejected (401)")
elif r.status_code == 200:
    info("Auth disabled — invalid token still accepted")

# =============================================
print("\n--- 6. Billing & Usage ---")

r = requests.get(f"{BASE}/v1/admin/tenants/tnt_default/billing?year=2026&month=5", timeout=5)
if r.status_code == 200 and r.json().get("period") == "2026-05":
    p("Billing API (monthly report)")
else:
    f("Billing", f"got {r.status_code}")

r = requests.get(f"{BASE}/v1/admin/tenants/tnt_default/usage?days=7", timeout=5)
if r.status_code == 200:
    p("Usage API (recent stats)")
else:
    f("Usage", f"got {r.status_code}")

# =============================================
print("\n" + "=" * 50)
print(f"  Results: \033[92m{PASS} passed\033[0m, \033[91m{FAIL} failed\033[0m")
print("=" * 50)
if FAIL == 0:
    print("  \033[92m>>> ALL TESTS PASSED <<<\033[0m")
    sys.exit(0)
else:
    print(f"  \033[91m>>> {FAIL} TESTS FAILED <<<\033[0m")
    sys.exit(1)
