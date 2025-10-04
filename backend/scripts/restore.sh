#!/bin/bash
# PostgreSQL restore script
# Restores the database from a compressed backup file

set -euo pipefail

# Configuration from environment variables
DB_NAME="${POSTGRES_DB:-nfc_access}"
DB_USER="${POSTGRES_USER:-nfc}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-ops/backups}"

# Check if backup file is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "  No backups found in $BACKUP_DIR"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=================================="
echo "PostgreSQL Restore"
echo "=================================="
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup file: $BACKUP_FILE"
echo ""
echo "⚠️  WARNING: This will DROP and recreate the database!"
echo "⚠️  All existing data will be lost!"
echo ""

# Safety check for production
if [ "${DJANGO_ENV:-dev}" = "production" ] || [ "${DJANGO_ENV:-dev}" = "prod" ]; then
    echo "🛑 PRODUCTION ENVIRONMENT DETECTED!"
    echo "   Extra confirmation required."
    echo ""
    read -p "Type 'RESTORE PRODUCTION' to continue: " confirm
    if [ "$confirm" != "RESTORE PRODUCTION" ]; then
        echo "Restore cancelled."
        exit 1
    fi
else
    read -p "Type 'yes' to continue: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled."
        exit 1
    fi
fi

echo ""
echo "Creating pre-restore backup..."
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
PRE_RESTORE_BACKUP="${BACKUP_DIR}/${DB_NAME}_pre-restore_${TIMESTAMP}.sql.gz"

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    | gzip > "$PRE_RESTORE_BACKUP" || echo "  (Pre-restore backup failed, continuing anyway)"

if [ -f "$PRE_RESTORE_BACKUP" ]; then
    BACKUP_SIZE=$(du -h "$PRE_RESTORE_BACKUP" | cut -f1)
    echo "✓ Pre-restore backup created: $PRE_RESTORE_BACKUP ($BACKUP_SIZE)"
fi

echo ""
echo "Restoring database..."

# Decompress and restore
gunzip -c "$BACKUP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --set ON_ERROR_STOP=on

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Database restored successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Run migrations: python manage.py migrate"
    echo "2. Verify data integrity"
    echo "3. Test application functionality"
else
    echo ""
    echo "✗ Restore failed!"
    echo ""
    echo "You can restore from pre-restore backup:"
    echo "  $PRE_RESTORE_BACKUP"
    exit 1
fi

echo ""
echo "=================================="
echo "Restore complete!"
echo "=================================="

