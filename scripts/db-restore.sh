#!/bin/sh
# Restore the HCOS database from a backup produced by db-backup.sh.
#
# Run on the server from /opt/hcos:
#   ./scripts/db-restore.sh backups/hcos_YYYYMMDD_HHMMSS.sql.gz
#   ./scripts/db-restore.sh backups/hcos_YYYYMMDD_HHMMSS.sql.gz.enc   # encrypted
#
# Encrypted dumps need the same passphrase used to create them — export it as
# BACKUP_ENCRYPTION_PASSPHRASE first (it lives in .env.prod). The dump is piped
# straight into psql in the running db container; --clean dumps drop & recreate
# objects, so this restores a full snapshot over the current database.
set -eu

FILE="${1:?usage: db-restore.sh <backups/hcos_*.sql.gz[.enc]>}"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
DBUSER="${POSTGRES_USER:-hcos}"
DBNAME="${POSTGRES_DB:-hcos}"

echo "Restoring $FILE into the running db container…"

decrypt() {
  case "$FILE" in
    *.enc)
      : "${BACKUP_ENCRYPTION_PASSPHRASE:?set BACKUP_ENCRYPTION_PASSPHRASE to decrypt}"
      openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_ENCRYPTION_PASSPHRASE -in "$FILE" ;;
    *)
      cat "$FILE" ;;
  esac
}

decrypt | gunzip -c | $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$DBUSER" -d "$DBNAME"
echo "Restore complete."
