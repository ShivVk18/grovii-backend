#!/usr/bin/env bash
# Wait until API_URL serves release SHA (first 12 chars) and /ready is ok, then
# check /health/deep. Exits non-zero after ~15 minutes (deploy failed or stuck:
# see docs/RUNBOOK.md "Roll back").
set -euo pipefail
api="${1:?api url}"; want="${2:?release sha}"; want="${want:0:12}"
for i in $(seq 1 90); do
  live=$(curl -fsS -m 10 "$api/health" 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("release",""))' || true)
  if [ "${live:0:12}" = "$want" ] && curl -fsS -m 10 "$api/ready" >/dev/null; then
    echo "release $want is live and ready"
    curl -sS -m 10 "$api/health/deep"; echo
    exit 0
  fi
  echo "waiting ($i/90): live=${live:-none}"
  sleep 10
done
echo "release $want did not become ready" >&2
exit 1
