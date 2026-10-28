#!/usr/bin/env bash
# Back up the Grovii Postgres database (custom format, compressed).
#
#   DATABASE_URL=postgresql://... scripts/backup_db.sh [OUT_DIR]
#
# Writes OUT_DIR/grovii-<UTC timestamp>.dump plus a .sha256, deletes local
# backups older than BACKUP_KEEP_DAYS (default 14), and copies the file to
# BACKUP_S3_URI (e.g. s3://bucket/grovii/) when set and the aws CLI exists.
# On Render, managed daily backups exist too; this is the off-site copy.
set -euo pipefail
: "${DATABASE_URL:?set DATABASE_URL}"
OUT_DIR="${1:-deploy/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
mkdir -p "$OUT_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="$OUT_DIR/grovii-$stamp.dump"

start=$(date +%s)
pg_dump --format=custom --compress=6 --no-owner --no-privileges --file="$file" "$DATABASE_URL"
( cd "$OUT_DIR" && shasum -a 256 "$(basename "$file")" > "$(basename "$file").sha256" )
echo "backup: $file ($(du -h "$file" | cut -f1), $(( $(date +%s) - start ))s)"

if [ -n "${BACKUP_S3_URI:-}" ]; then
  if command -v aws >/dev/null; then
    aws s3 cp "$file" "$BACKUP_S3_URI" && aws s3 cp "$file.sha256" "$BACKUP_S3_URI"
  else
    echo "warning: BACKUP_S3_URI set but aws CLI not installed; off-site copy skipped" >&2
  fi
fi

find "$OUT_DIR" -name 'grovii-*.dump*' -type f -mtime +"$KEEP_DAYS" -print -delete
