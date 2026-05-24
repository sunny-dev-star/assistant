#!/bin/bash
# ============================================================================
# Assistant Framework - Integration Test Suite
# Usage: ./tests/test_integration.sh [BASE_URL] [AUTH_TOKEN]
# ============================================================================
set -euo pipefail

BASE="${1:-http://localhost:8000}"
TOKEN="${2:-}"
PASS=0
FAIL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; ((PASS++)); }
log_fail() { echo -e "  ${RED}[FAIL]${NC} $1 — $2"; ((FAIL++)); }
log_info() { echo -e "  ${YELLOW}[INFO]${NC} $1"; }

auth_header() {
    if [ -n "$TOKEN" ]; then
        echo "-H 'Authorization: Bearer $TOKEN'"
    else
        echo ""
    fi
}

# Helper: POST with optional auth
post_chat() {
    local data="$1"
    if [ -n "$TOKEN" ]; then
        curl -s -X POST "$BASE/v1/chat" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X POST "$BASE/v1/chat" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

echo "=========================================="
echo "  Assistant Integration Test Suite"
echo "  Target: $BASE"
echo "  Auth:   $([ -n "$TOKEN" ] && echo "ON (Bearer)" || echo "OFF (dev mode)")"
echo "=========================================="

# =============================================
echo -e "\n--- 1. Health & Infrastructure ---"

# 1.1 Health check
R=$(curl -s -w "\n%{http_code}" "$BASE/health")
CODE=$(echo "$R" | tail -1)
BODY=$(echo "$R" | sed '$d')
if [ "$CODE" = "200" ]; then
    log_pass "Health check (200)"
else
    log_fail "Health check" "got $CODE"
fi

# 1.2 Root endpoint
R=$(curl -s -w "\n%{http_code}" "$BASE/")
CODE=$(echo "$R" | tail -1)
if [ "$CODE" = "200" ]; then log_pass "Root endpoint"; else log_fail "Root" "got $CODE"; fi

# 1.3 Prometheus metrics
R=$(curl -s -w "\n%{http_code}" "$BASE/metrics")
CODE=$(echo "$R" | tail -1)
BODY=$(echo "$R" | sed '$d')
if [ "$CODE" = "200" ] && echo "$BODY" | grep -q "agent_chat_requests_total"; then
    log_pass "Prometheus metrics"
else
    log_fail "Prometheus metrics" "got $CODE or missing metrics"
fi

# 1.4 OpenAPI docs
R=$(curl -s -w "\n%{http_code}" "$BASE/openapi.json")
CODE=$(echo "$R" | tail -1)
if [ "$CODE" = "200" ]; then log_pass "OpenAPI spec"; else log_fail "OpenAPI" "got $CODE"; fi

# =============================================
echo -e "\n--- 2. Skills ---"

# 2.1 Skills list
R=$(curl -s "$BASE/v1/skills")
TOTAL=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
if [ "$TOTAL" -ge 3 ]; then
    log_pass "Skills loaded: $TOTAL skills"
else
    log_fail "Skills" "expected >=3, got $TOTAL"
fi

# 2.2 Elder care skill detail
R=$(curl -s -w "\n%{http_code}" "$BASE/v1/skills/elder_care")
CODE=$(echo "$R" | tail -1)
BODY=$(echo "$R" | sed '$d')
TOOLS=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('tools',[])))" 2>/dev/null || echo "0")
if [ "$CODE" = "200" ] && [ "$TOOLS" -ge 4 ]; then
    log_pass "Elder care skill: $TOOLS tools"
else
    log_fail "Elder care" "got $CODE, $TOOLS tools"
fi

# =============================================
echo -e "\n--- 3. Chat (Basic) ---"

# 3.1 Simple greeting
R=$(post_chat '{"message":"你好","user_id":"test_user_001"}')
REPLY=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('reply',''))" 2>/dev/null || echo "")
SESSION=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
if [ -n "$REPLY" ] && [ "$REPLY" != "None" ]; then
    log_pass "Basic chat reply received"
    log_info "Reply: ${REPLY:0:60}..."
    log_info "Session: $SESSION"
else
    log_fail "Basic chat" "empty reply"
fi

# 3.2 Session continuity
if [ -n "$SESSION" ] && [ "$SESSION" != "None" ]; then
    R2=$(post_chat "{\"message\":\"刚才我说了什么？\",\"user_id\":\"test_user_001\",\"session_id\":\"$SESSION\"}")
    SESSION2=$(echo "$R2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
    if [ "$SESSION2" = "$SESSION" ]; then
        log_pass "Session continuity (same session_id)"
    else
        log_fail "Session continuity" "expected $SESSION, got $SESSION2"
    fi
fi

# =============================================
echo -e "\n--- 4. Chat (Tool Calling) ---"

# 4.1 Weather query
R=$(post_chat '{"message":"今天成都天气怎么样？","user_id":"test_user_002"}')
REPLY=$(echo "$R" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('reply',''))" 2>/dev/null || echo "")
if [ -n "$REPLY" ] && [ "$REPLY" != "None" ]; then
    log_pass "Weather tool call"
    log_info "Reply: ${REPLY:0:80}..."
else
    log_fail "Weather tool" "empty reply"
fi

# =============================================
echo -e "\n--- 5. Auth Mode (if enabled) ---"

# 5.1 No token (should 401 if auth enabled, 200 if dev mode)
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"test","user_id":"u1"}')
CODE=$(echo "$R" | tail -1)
if [ "$CODE" = "401" ]; then
    log_pass "No-token request correctly rejected (401)"
elif [ "$CODE" = "200" ]; then
    log_info "Auth disabled (dev mode) — 200 without token"
else
    log_fail "Auth check" "unexpected $CODE"
fi

# 5.2 Invalid token (if auth enabled)
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE/v1/chat" \
    -H "Authorization: Bearer ak_invalid_key" \
    -H "Content-Type: application/json" \
    -d '{"message":"test","user_id":"u1"}')
CODE=$(echo "$R" | tail -1)
if [ "$CODE" = "401" ]; then
    log_pass "Invalid token rejected (401)"
elif [ "$CODE" = "200" ]; then
    log_info "Auth disabled — invalid token still accepted"
fi

# =============================================
echo -e "\n--- 6. Billing & Usage ---"

R=$(curl -s "$BASE/v1/admin/tenants/tnt_default/billing?year=2026&month=5")
PERIOD=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('period',''))" 2>/dev/null || echo "")
if [ "$PERIOD" = "2026-05" ]; then
    log_pass "Billing API"
else
    log_fail "Billing" "unexpected period: $PERIOD"
fi

# =============================================
# Summary
# =============================================
echo ""
echo "=========================================="
echo -e "  Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
echo "=========================================="

if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}>>> ALL TESTS PASSED <<<${NC}"
    exit 0
else
    echo -e "  ${RED}>>> $FAIL TESTS FAILED <<<${NC}"
    exit 1
fi
