#!/bin/sh
# Periodic pg_dump of the HCOS database into /backups, with retention pruning.
#
# Runs as the `db-backup` sidecar (see docker-compose.prod.yml): one backup on
# start (so every redeploy/reboot produces a fresh snapshot), then every
# BACKUP_INTERVAL_SECONDS. Connection comes from the standard PG* env vars.
#
# Optional at-rest encryption: if BACKUP_ENCRYPTION_PASSPHRASE is set, dumps are
# encrypted with AES-256 (openssl) and written as *.sql.gz.enc. Decrypt/restore
# with scripts/db-restore.sh. Without a passphrase, dumps are plain gzip.
set -eu

DIR=/backups
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
PASS="${BACKUP_ENCRYPTION_PASSPHRASE:-}"

mkdir -p "$DIR"

backup() {
  ts="$(date -u +%Y%m%d_%H%M%S)"
  if [ -n "$PASS" ]; then
    out="$DIR/hcos_${ts}.sql.gz.enc"
    tmp="${out}.partial"
    echo "[db-backup] dumping ${PGDATABASE} -> ${out} (encrypted)"
    pg_dump --clean --if-exists --no-owner --no-privileges \
      | gzip -9 \
      | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_ENCRYPTION_PASSPHRASE \
      > "$tmp"
  else
    out="$DIR/hcos_${ts}.sql.gz"
    tmp="${out}.partial"
    echo "[db-backup] dumping ${PGDATABASE} -> ${out}"
    pg_dump --clean --if-exists --no-owner --no-privileges | gzip -9 > "$tmp"
  fi
  mv "$tmp" "$out"
  echo "[db-backup] ok: $(du -h "$out" | cut -f1)"
  # Retention: drop dumps older than N days (both plain and encrypted).
  find "$DIR" \( -name 'hcos_*.sql.gz' -o -name 'hcos_*.sql.gz.enc' \) -type f -mtime +"$RETENTION_DAYS" -print -delete 2>/dev/null || true
}

echo "[db-backup] starting; interval=${INTERVAL}s retention=${RETENTION_DAYS}d encrypted=$([ -n "$PASS" ] && echo yes || echo no)"
while true; do
  if ! backup; then
    echo "[db-backup] backup failed, will retry next cycle" >&2
    rm -f "$DIR"/hcos_*.partial 2>/dev/null || true
  fi
  sleep "$INTERVAL"
done
