#!/usr/bin/env bash
# Rollback drill on the local compose staging stack (never production).
#   cd deploy && OLD=v1 NEW=v2 OLD_HEAD=b8c9d0e1f2a3 ../scripts/drill_rollback.sh
# OLD/NEW are grovii-backend image tags; OLD_HEAD is the old release's migration head.
set -euo pipefail
OLD="${OLD:?old image tag}"; NEW="${NEW:?new image tag}"; OLD_HEAD="${OLD_HEAD:?old migration head}"
API="http://localhost:${API_PORT:-8400}"
DC="docker compose --env-file staging.env"
REL_BACKEND() { RELEASE="$1" $DC up -d --no-build --no-deps "${@:2}" >/dev/null 2>&1; }
wait_up() { for _ in $(seq 1 60); do curl -sf -m 2 "$API/health" >/dev/null && return 0; sleep 1; done; echo "API did not come up" >&2; return 1; }
db_rev() { $DC exec -T postgres psql -U grovii -d grovii -At -c "select version_num from alembic_version"; }
# One account for the whole drill (sign-up is rate limited per IP).
DRILL_EMAIL="rb_$RANDOM$RANDOM@example.com"
smoke() {
  local email="$DRILL_EMAIL" pw="violet-lamp-orbit-27" jar; jar="$(mktemp)"
  curl -s -o /dev/null -X POST "$API/auth/register" -H 'Content-Type: application/json' \
    -d "{\"username\":\"${email%@*}\",\"email\":\"$email\",\"password\":\"$pw\"}" || true
  curl -sf -o /dev/null -c "$jar" -X POST "$API/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$email\",\"password\":\"$pw\"}"
  local code; code=$(curl -s -o /dev/null -w '%{http_code}' -b "$jar" "$API/storyboards")
  rm -f "$jar"; echo "sign-up + sign-in + list storyboards -> HTTP $code"
}
step() { echo; echo "== $* ($(date -u +%T))"; }

step "0. NEW ($NEW) is live"
REL_BACKEND "$NEW" api worker; wait_up
echo "db revision: $(db_rev)   /health: $(curl -s "$API/health")"; smoke

step "1. App-only rollback to OLD ($OLD), schema stays at NEW's head"
t0=$(date +%s); REL_BACKEND "$OLD" api worker; wait_up
echo "rolled back in $(( $(date +%s)-t0 ))s; db revision: $(db_rev)   /health: $(curl -s "$API/health")"; smoke

step "2. Schema rollback: downgrade with the NEW image (it has the migration script), keep OLD running"
t0=$(date +%s)
RELEASE="$NEW" $DC run --rm --no-deps --entrypoint alembic migrate downgrade "$OLD_HEAD" 2>&1 | grep -E "Running|ERROR" || true
echo "downgraded in $(( $(date +%s)-t0 ))s; db revision: $(db_rev)"; smoke

step "3. Roll forward to NEW: migrate, then start NEW"
t0=$(date +%s)
RELEASE="$NEW" $DC run --rm --no-deps migrate 2>&1 | grep -E "Running|ERROR" || true
REL_BACKEND "$NEW" api worker; wait_up
echo "rolled forward in $(( $(date +%s)-t0 ))s; db revision: $(db_rev)"
echo "/ready: $(curl -s "$API/ready")"; smoke
