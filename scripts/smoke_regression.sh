#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-18090}"
BASE_URL="http://${HOST}:${PORT}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
LOG_FILE="${LOG_FILE:-/tmp/keble_smoke_uvicorn.log}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python runtime not found at: $PYTHON_BIN"
  echo "Run: ./scripts/dev_bootstrap.sh"
  exit 1
fi

fail() {
  echo "SMOKE FAIL: $1"
  exit 1
}

pass() {
  echo "SMOKE PASS: $1"
}

"$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
SERVER_PID=$!

cleanup() {
  if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

READY=0
for _ in $(seq 1 60); do
  if curl -fsS "$BASE_URL/healthz" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.2
done
[ "$READY" = "1" ] || fail "server startup timeout, see $LOG_FILE"
pass "server started"

EXPECTED_ROUTE_COUNT=$("$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path
manifest=Path("app/route_manifest.json")
payload=json.loads(manifest.read_text())
print(len(payload.get("routes", [])))
PY
)
SUMMARY_JSON="$(curl -fsS "$BASE_URL/api/v2/_meta/summary")"
SUMMARY_ROUTE_COUNT="$(printf '%s' "$SUMMARY_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("count", -1))')"
[ "$SUMMARY_ROUTE_COUNT" = "$EXPECTED_ROUTE_COUNT" ] || fail "route summary mismatch expected=$EXPECTED_ROUTE_COUNT got=$SUMMARY_ROUTE_COUNT"
pass "meta summary count"

MISSING_COUNT=$("$PYTHON_BIN" - <<'PY'
import json,re
from pathlib import Path
manifest=json.loads(Path("app/route_manifest.json").read_text())["routes"]
text=Path("app/routes/priority_routes.py").read_text()
impl=set(re.findall(r'@router\.(?:get|post|put|patch|delete)\("([^"]+)"\)',text))
missing=[r["path"] for r in manifest if r["path"] not in impl]
print(len(missing))
PY
)
[ "$MISSING_COUNT" = "0" ] || fail "manifest routes missing in priority router: $MISSING_COUNT"
pass "manifest coverage 100%"

LOGIN_JSON="$(curl -fsS -X POST "$BASE_URL/api/v2/users/public/obj/login" -H 'Content-Type: application/json' -d '{"email":"owner@keble.local","password":"owner-password"}')"
TOKEN="$(printf '%s' "$LOGIN_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("accessToken",""))')"
[ -n "$TOKEN" ] || fail "login token missing"
AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")
pass "login flow"

curl -fsS "$BASE_URL/api/v2/configs/public/obj" >/dev/null
curl -fsS "$BASE_URL/api/v2/configs/public/contact/obj" >/dev/null
curl -fsS "$BASE_URL/api/v2/configs/public/notification/obj?language=en&notification_type=MAINTENANCE" >/dev/null
pass "public configs"

BLOG_LIST_JSON="$(curl -fsS "$BASE_URL/api/v2/contents/blogs/public/list?language=en&limit=2")"
BLOG_SLUG="$(printf '%s' "$BLOG_LIST_JSON" | "$PYTHON_BIN" -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["slug"] if rows else "")')"
[ -n "$BLOG_SLUG" ] || fail "blog list returned empty"
curl -fsS "$BASE_URL/api/v2/contents/blogs/public/obj/$BLOG_SLUG?language=en" >/dev/null
curl -fsS "$BASE_URL/api/v2/contents/blogs/public/pagination/obj?language=en&limit=1" >/dev/null
curl -fsS "$BASE_URL/api/v2/blogs/en/1" >/dev/null
pass "public blog routes"

SUPPORT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v2/supports/public/obj" -H 'Content-Type: application/json' -d '{"name":"Smoke","email":"smoke@example.com","message":"smoke test"}')"
SUPPORT_OK="$(printf '%s' "$SUPPORT_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(str(bool(json.load(sys.stdin).get("success"))).lower())')"
[ "$SUPPORT_OK" = "true" ] || fail "support create failed"
pass "public support route"

TASK_JSON="$(curl -fsS -X POST "$BASE_URL/api/v2/features/amz-product-reports/owner/tasks/obj" "${AUTH_HEADER[@]}" -H 'Content-Type: application/json' -d '{"asin":"B0SMOKE1234","marketplace":"US","keyword":"kettle"}')"
TASK_ID="$(printf '%s' "$TASK_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("taskId",""))')"
REPORT_ID="$(printf '%s' "$TASK_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("reportId",""))')"
[ -n "$TASK_ID" ] || fail "report task id missing"
[ -n "$REPORT_ID" ] || fail "report id missing"
curl -fsS "$BASE_URL/api/v2/features/amz-product-reports/optional-owner/tasks/obj?task_id=$TASK_ID" >/dev/null
curl -fsS "$BASE_URL/api/v2/features/amz-product-reports/optional-owner/product-reports/overview/obj/$REPORT_ID" >/dev/null
curl -fsS "$BASE_URL/api/v2/features/amz-product-reports/optional-owner/product-reports/brands-metrics/obj/$REPORT_ID" >/dev/null
curl -fsS "$BASE_URL/api/v2/features/amz-product-reports/owner/asin-info/obj?asin=B08N5L5R6P&marketplace=US" "${AUTH_HEADER[@]}" >/dev/null
curl -fsS "$BASE_URL/api/v2/features/amz-product-reports/owner/products-preview/obj?asin=B08N5L5R6P&marketplace=US&keyword=blender" "${AUTH_HEADER[@]}" >/dev/null
pass "report routes"

curl -fsS "$BASE_URL/api/v2/features/amz-shuffle-products/public/root-categories/obj?marketplace=US" >/dev/null
curl -fsS "$BASE_URL/api/v2/features/amz-shuffle-products/user/searched-categories/obj?marketplace=US&keyword=home" "${AUTH_HEADER[@]}" >/dev/null
curl -fsS -X POST "$BASE_URL/api/v2/features/amz-shuffle-products/user/obj" "${AUTH_HEADER[@]}" -H 'Content-Type: application/json' -d '{"marketplace":"US","categoryIds":["home-kitchen"],"keywords":["blender"],"noLessThan":3}' >/dev/null
curl -fsS "$BASE_URL/api/v2/features/configs/owner/shipping-and-exchange-rates/obj?amazon_marketplace=US" "${AUTH_HEADER[@]}" >/dev/null
pass "shuffle + shipping routes"

curl -fsS "$BASE_URL/api/v2/memberships/owner/list?limit=2" "${AUTH_HEADER[@]}" >/dev/null
curl -fsS -X POST "$BASE_URL/api/v2/memberships/owner/obj" "${AUTH_HEADER[@]}" -H 'Content-Type: application/json' -d '{"membershipId":"membership_growth"}' >/dev/null
curl -fsS "$BASE_URL/api/v2/token-services/public/list" >/dev/null
curl -fsS "$BASE_URL/api/v2/token-containers/owner/obj" "${AUTH_HEADER[@]}" >/dev/null
pass "membership + token routes"

curl -fsS "$BASE_URL/api/v2/coupons/public/obj?coupon_code=WELCOME10" >/dev/null
curl -fsS "$BASE_URL/api/v2/coupons/owner/consumable/obj?coupon_code=WELCOME10&currency=USD&marketplace=US" "${AUTH_HEADER[@]}" >/dev/null
pass "coupon routes"

CLOUD_JSON="$(curl -fsS -X POST "$BASE_URL/api/v2/cloud-storages/user/obj" "${AUTH_HEADER[@]}" -H 'Content-Type: application/json' -d '{"fileName":"smoke.csv","fileSize":128,"contentType":"text/csv"}')"
CLOUD_ID="$(printf '%s' "$CLOUD_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("id",""))')"
[ -n "$CLOUD_ID" ] || fail "cloud storage id missing"
curl -fsS "$BASE_URL/api/v2/cloud-storages/user/obj" "${AUTH_HEADER[@]}" >/dev/null
curl -fsS "$BASE_URL/api/v2/cloud-storages/user/obj/$CLOUD_ID" "${AUTH_HEADER[@]}" >/dev/null
pass "cloud storage routes"

ORG_JSON="$(curl -fsS -X POST "$BASE_URL/api/v2/orgs/user/org/obj" "${AUTH_HEADER[@]}" -H 'Content-Type: application/json' -d '{"name":"Smoke Org"}')"
ORG_ID="$(printf '%s' "$ORG_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("id",""))')"
[ -n "$ORG_ID" ] || fail "org id missing"
curl -fsS "$BASE_URL/api/v2/orgs/public/obj?org_id=$ORG_ID" >/dev/null
curl -fsS "$BASE_URL/api/v2/orgs/user/org?org_id=$ORG_ID" "${AUTH_HEADER[@]}" >/dev/null
pass "org query routes"

PROGRESS_KEY="report:$TASK_ID"
curl -fsS "$BASE_URL/api/v2/progresses/user/obj?progress_key=$PROGRESS_KEY" "${AUTH_HEADER[@]}" >/dev/null
curl -fsS -X POST "$BASE_URL/api/v2/progresses/user/list" "${AUTH_HEADER[@]}" -H 'Content-Type: application/json' -d "{\"progress_keys\":[\"$PROGRESS_KEY\"]}" >/dev/null
pass "progress routes"

curl -fsS -X POST "$BASE_URL/api/v2/token/tokens" -H 'Content-Type: application/json' -d '{"text":"smoke regression"}' >/dev/null
pass "token utility route"

echo "SMOKE PASS: all checks completed"
