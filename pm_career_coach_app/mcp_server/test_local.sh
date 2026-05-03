#!/usr/bin/env bash
# test_local.sh — smoke-test the PM Career Coach MCP server locally.
#
# Usage (from pm_career_coach_app/):
#   bash mcp_server/test_local.sh
#
# Prerequisites:
#   - pip install -r mcp_server/requirements.txt
#   - MCP_BEARER_TOKEN, and at least one LLM key, must be set OR a .env file
#     present in pm_career_coach_app/
#
# The script:
#   1. Starts the server on port 7860 with a known test token
#   2. Runs auth + protocol tests
#   3. Kills the server and reports pass/fail

set -euo pipefail

PORT=7860
BASE_URL="http://localhost:${PORT}"
TEST_TOKEN="test-token-$(date +%s)"
WRONG_TOKEN="definitely-wrong-token"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pass() { echo "  ✅  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌  FAIL: $1"; FAIL=$((FAIL + 1)); }

check_status() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [ "$actual" = "$expected" ]; then
        pass "$label (HTTP $actual)"
    else
        fail "$label — expected HTTP $expected, got HTTP $actual"
    fi
}

check_header() {
    local label="$1"
    local header_name="$2"
    local expected_substr="$3"
    local headers="$4"
    if echo "$headers" | grep -qi "$expected_substr"; then
        pass "$label (header present: $header_name)"
    else
        fail "$label — $header_name header missing or wrong. Got: $headers"
    fi
}

check_body() {
    local label="$1"
    local expected_substr="$2"
    local body="$3"
    if echo "$body" | grep -q "$expected_substr"; then
        pass "$label (body contains: $expected_substr)"
    else
        fail "$label — body does not contain '$expected_substr'. Got: $body"
    fi
}

wait_for_server() {
    local max_wait=15
    local elapsed=0
    echo "  Waiting for server to start..."
    while ! curl -s "${BASE_URL}/health" > /dev/null 2>&1; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ "$elapsed" -ge "$max_wait" ]; then
            echo "  Server did not start within ${max_wait}s — aborting."
            exit 1
        fi
    done
    echo "  Server is up after ${elapsed}s."
}

# ---------------------------------------------------------------------------
# Start server
# ---------------------------------------------------------------------------

echo ""
echo "========================================"
echo " PM Career Coach MCP Server — local test"
echo "========================================"
echo ""
echo "Starting server on port ${PORT} with test token..."

# Export test token; preserve any existing LLM / Pinecone keys from the
# calling environment so real API calls (step 6) can succeed.
export MCP_BEARER_TOKEN="${TEST_TOKEN}"

# cd to pm_career_coach_app/ directory (parent of mcp_server/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
cd "$APP_DIR"

# Load .env if present (for LLM / Pinecone keys)
if [ -f ".env" ]; then
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
    # Override with our test token after sourcing .env
    export MCP_BEARER_TOKEN="${TEST_TOKEN}"
fi

python -m mcp_server.server &
SERVER_PID=$!
trap 'echo ""; echo "Stopping server (PID ${SERVER_PID})..."; kill "${SERVER_PID}" 2>/dev/null; wait "${SERVER_PID}" 2>/dev/null; echo "Done."' EXIT

wait_for_server
echo ""

# ---------------------------------------------------------------------------
# Step 1 — GET /health (no auth) should return 200
# ---------------------------------------------------------------------------
echo "Step 1: GET /health (no auth) — expect 200"
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health")
check_status "GET /health returns 200" "200" "$HEALTH_STATUS"

HEALTH_BODY=$(curl -s "${BASE_URL}/health")
check_body "/health body contains 'ok'" '"ok"' "$HEALTH_BODY"
echo ""

# ---------------------------------------------------------------------------
# Step 2 — POST /mcp without Authorization — expect 401 with WWW-Authenticate
# ---------------------------------------------------------------------------
echo "Step 2: POST /mcp without Authorization header — expect 401"
RESPONSE_HEADERS=$(curl -s -D - -o /dev/null -X POST "${BASE_URL}/mcp" \
    -H "Content-Type: application/json" \
    -d '{}')
NO_AUTH_STATUS=$(echo "$RESPONSE_HEADERS" | head -1 | grep -o '[0-9]\{3\}')
check_status "No auth → 401" "401" "$NO_AUTH_STATUS"
check_header "WWW-Authenticate header present" "WWW-Authenticate" 'WWW-Authenticate' "$RESPONSE_HEADERS"
echo ""

# ---------------------------------------------------------------------------
# Step 3 — POST /mcp with wrong token — expect 401
# ---------------------------------------------------------------------------
echo "Step 3: POST /mcp with wrong bearer token — expect 401"
WRONG_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/mcp" \
    -H "Authorization: Bearer ${WRONG_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{}')
check_status "Wrong token → 401" "401" "$WRONG_STATUS"
echo ""

# ---------------------------------------------------------------------------
# Step 4 — MCP initialize + tools/list with correct token — expect 200 + 5 tools
# ---------------------------------------------------------------------------
echo "Step 4: MCP initialize → tools/list with correct token — expect 200 + 5 tools"

INIT_PAYLOAD='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-client","version":"0.1.0"}}}'

# Capture response headers and body together
INIT_RAW=$(curl -s -D - -X POST "${BASE_URL}/mcp" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d "$INIT_PAYLOAD")

INIT_HTTP=$(echo "$INIT_RAW" | head -1 | grep -o '[0-9]\{3\}')
SESSION_ID=$(echo "$INIT_RAW" | grep -i "mcp-session-id:" | awk '{print $2}' | tr -d '\r\n')

check_status "initialize → 200" "200" "$INIT_HTTP"

if [ -z "$SESSION_ID" ]; then
    fail "Mcp-Session-Id header missing from initialize response"
else
    pass "Mcp-Session-Id header present: ${SESSION_ID}"
fi

# Send initialized notification
INIT_NOTIF='{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'
curl -s -o /dev/null -X POST "${BASE_URL}/mcp" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Mcp-Session-Id: ${SESSION_ID}" \
    -d "$INIT_NOTIF" || true

# tools/list
TOOLS_PAYLOAD='{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
TOOLS_RAW=$(curl -s -X POST "${BASE_URL}/mcp" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: ${SESSION_ID}" \
    -d "$TOOLS_PAYLOAD")

# SSE responses prefix data lines with "data: "; strip it to get JSON
TOOLS_JSON=$(echo "$TOOLS_RAW" | sed 's/^data: //')

TOOL_COUNT=$(echo "$TOOLS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
tools = data.get('result', {}).get('tools', [])
print(len(tools))
" 2>/dev/null || echo "0")

if [ "$TOOL_COUNT" = "5" ]; then
    pass "tools/list returns exactly 5 tools"
else
    fail "tools/list — expected 5 tools, got ${TOOL_COUNT}. Raw: ${TOOLS_JSON}"
fi

# Verify all expected tool names are present
for TOOL_NAME in search_coaching_notes get_interview_coaching analyze_skill_gaps craft_career_positioning score_job_match; do
    if echo "$TOOLS_JSON" | grep -q "\"$TOOL_NAME\""; then
        pass "Tool present: $TOOL_NAME"
    else
        fail "Tool missing: $TOOL_NAME"
    fi
done
echo ""

# ---------------------------------------------------------------------------
# Step 5 — search_coaching_notes tool call (requires PINECONE_API_KEY)
# ---------------------------------------------------------------------------
echo "Step 5: tools/call search_coaching_notes (requires PINECONE_API_KEY)"

if [ -z "${PINECONE_API_KEY:-}" ]; then
    echo "  ⚠️  SKIP: PINECONE_API_KEY is not set — skipping live RAG search test."
    echo "       Set PINECONE_API_KEY in your environment or .env to enable this step."
else
    SEARCH_PAYLOAD=$(cat <<'EOF'
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_coaching_notes",
    "arguments": {"query": "PM behavioral interview", "top_k": 3}
  }
}
EOF
)
    SEARCH_RAW=$(curl -s -X POST "${BASE_URL}/mcp" \
        -H "Authorization: Bearer ${TEST_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -H "Mcp-Session-Id: ${SESSION_ID}" \
        -d "$SEARCH_PAYLOAD")

    SEARCH_JSON=$(echo "$SEARCH_RAW" | sed 's/^data: //')

    RESULT_COUNT=$(echo "$SEARCH_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
content = data.get('result', {}).get('content', [])
# content is a list with one text block containing the JSON array
text = content[0].get('text', '[]') if content else '[]'
results = json.loads(text)
print(len(results))
" 2>/dev/null || echo "0")

    if [ "$RESULT_COUNT" -gt "0" ] 2>/dev/null; then
        pass "search_coaching_notes returned ${RESULT_COUNT} result(s)"
    else
        fail "search_coaching_notes returned 0 results — check PINECONE_API_KEY and index name"
    fi
fi
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL=$((PASS + FAIL))
echo "========================================"
echo " Results: ${PASS}/${TOTAL} passed"
echo "========================================"
echo ""

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
