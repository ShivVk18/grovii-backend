#!/bin/sh
# Container entrypoint: picks what this container runs.
set -eu
role="${1:-api}"
export GROVII_ROLE="$role"
case "$role" in
  api)
    # One process per container; scale with more containers/instances.
    # Proxy headers are not trusted: the client IP comes from the Next.js proxy
    # with a shared secret (see src/services/rate_limit.py).
    exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-1}" --no-access-log --timeout-graceful-shutdown 20
    ;;
  worker)
    exec python -m src.services.worker
    ;;
  migrate)
    exec alembic upgrade head
    ;;
  reaper)
    exec python -m src.services.reaper
    ;;
  *)
    exec "$@"
    ;;
esac
