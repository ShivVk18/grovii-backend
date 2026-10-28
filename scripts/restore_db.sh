#!/usr/bin/env bash
# Restore a Grovii backup into a database.
#
#   TARGET_DATABASE_URL=postgresql://.../grovii_restore scripts/restore_db.sh FILE.dump
#
# Safety: refuses targets whose database name doesn't end in _restore, _test or
# _staging unless CONFIRM_RESTORE_TO_PRODUCTION=yes (overwriting production is
# a last-resort step; see docs/RUNBOOK.md). Verifies the checksum first, then
# prints the migration version and row counts so the result can be checked.
set -euo pipefail
file="${1:?usage: restore_db.sh FILE.dump}"
: "${TARGET_DATABASE_URL:?set TARGET_DATABASE_URL}"
dbname="${TARGET_DATABASE_URL##*/}"; dbname="${dbname%%\?*}"
case "$dbname" in
  *_restore|*_test|*_staging) ;;
  *) [ "${CONFIRM_RESTORE_TO_PRODUCTION:-}" = "yes" ] || { echo "refusing to restore into '$dbname'" >&2; exit 2; } ;;
esac
if [ -f "$file.sha256" ]; then
  ( cd "$(dirname "$file")" && shasum -a 256 -c "$(basename "$file").sha256" )
fi

start=$(date +%s)
pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error --jobs=4 \
  --dbname="$TARGET_DATABASE_URL" "$file"
echo "restore: done in $(( $(date +%s) - start ))s"

psql "$TARGET_DATABASE_URL" -At -c "SELECT 'alembic_version=' || version_num FROM alembic_version"
for t in users storyboards scenes captions hashtags hooks music trends repurpose jobs user_sessions; do
  n=$(psql "$TARGET_DATABASE_URL" -At -c "SELECT count(*) FROM $t" 2>/dev/null || echo "missing")
  echo "$t=$n"
done
