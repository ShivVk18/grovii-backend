#!/usr/bin/env bash
# Drill: does a queued job survive a Redis restart? (local compose staging only)
#   cd deploy && ../scripts/drill_redis_restart.sh
set -euo pipefail
API="${API:-http://localhost:${API_PORT:-8400}}"
DC="docker compose --env-file staging.env"
REDIS_PASSWORD="$(grep ^REDIS_PASSWORD staging.env | cut -d= -f2)"
rcli() { $DC exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning "$@"; }
jar="$(mktemp)"; trap 'rm -f "$jar"' EXIT

echo "1. stop the worker (so the job waits in the queue)"
$DC stop worker >/dev/null

echo "2. create a user and queue one generation"
email="drill_$RANDOM$RANDOM@example.com"; pw="violet-lamp-orbit-27"
curl -sf -o /dev/null -X POST "$API/auth/register" -H 'Content-Type: application/json' \
  -d "{\"username\":\"${email%@*}\",\"email\":\"$email\",\"password\":\"$pw\"}"
curl -sf -o /dev/null -c "$jar" -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$email\",\"password\":\"$pw\"}"
csrf="$(awk '/grovii_csrf/ {print $7}' "$jar")"
job="$(curl -sf -b "$jar" -X POST "$API/storyboards/generate" -H 'Content-Type: application/json' -H "X-CSRF-Token: $csrf" \
  -d '{"idea":"A 30 second espresso routine for busy mornings","goal":"educate","tone":"calm","style":"talking_head","audience":"Coffee lovers","duration":30,"platform":"reels"}' \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["job_id"])')"
echo "   job $job; queue length before restart: $(rcli LLEN rq:queue:storyboards)"

echo "3. restart Redis (append-only file on a volume)"
t0=$(date +%s); $DC restart redis >/dev/null
until rcli PING 2>/dev/null | grep -q PONG; do sleep 1; done
echo "   Redis back in $(( $(date +%s) - t0 ))s; queue length after restart: $(rcli LLEN rq:queue:storyboards)"
echo "   job still queued in Redis: $(rcli LPOS rq:queue:storyboards "$job" >/dev/null && echo yes || echo NO)"
echo "   API readiness: $(curl -s "$API/ready")"

echo "4. start the worker; it should pick the job up"
$DC start worker >/dev/null
for _ in $(seq 1 30); do
  st="$(curl -sf -b "$jar" "$API/storyboards/jobs/$job" | python3 -c 'import json,sys;print(json.load(sys.stdin)["status"])')"
  [ "$st" != "queued" ] && break; sleep 1
done
echo "   job status after worker start: $st"
