#!/bin/bash
# PostgreSQL backup script with rotation
# Backs up the database to ops/backups/ directory

set -euo pipefail

# Configuration from environment variables
DB_NAME="${POSTGRES_DB:-nfc_access}"
DB_USER="${POSTGRES_USER:-nfc}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-ops/backups}"
KEEP_BACKUPS="${KEEP_BACKUPS:-7}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "=================================="
echo "PostgreSQL Backup"
echo "=================================="
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup file: $BACKUP_FILE"
echo ""

# Perform backup
echo "Creating backup..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "✗ Backup failed!"
    exit 1
fi

# Rotate old backups
echo ""
echo "Rotating old backups (keeping last $KEEP_BACKUPS)..."
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l)

if [ "$BACKUP_COUNT" -gt "$KEEP_BACKUPS" ]; then
    # Delete oldest backups
    ls -1t "$BACKUP_DIR"/*.sql.gz | tail -n +$((KEEP_BACKUPS + 1)) | while read -r old_backup; do
        echo "  Removing: $old_backup"
        rm -f "$old_backup"
    done
    echo "✓ Rotation complete"
else
    echo "  No rotation needed ($BACKUP_COUNT backups)"
fi

echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "  No backups found"

echo ""
echo "=================================="
echo "Backup complete!"
echo "=================================="

