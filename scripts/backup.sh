#!/bin/bash
# ============================================================================
# Agent Framework - Database Backup Script
# Usage: ./scripts/backup.sh
# Cron: 0 2 * * * /path/to/scripts/backup.sh >> /var/log/agent-backup.log 2>&1
# ============================================================================

set -euo pipefail

# --- Config ---
DB_HOST="${DB_HOST:-agent-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-agent_db}"
DB_USER="${DB_USER:-agent}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# OSS config (optional, set to enable cloud upload)
OSS_BUCKET="${OSS_BUCKET:-}"
OSS_PATH="${OSS_PATH:-backups}"

# --- Functions ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    find "${BACKUP_DIR}" -name "agent_db_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
    log "Cleanup done."
}

upload_to_oss() {
    local file="$1"
    if [ -z "${OSS_BUCKET}" ]; then
        log "OSS_BUCKET not set, skipping cloud upload."
        return 0
    fi

    if command -v ossutil64 &>/dev/null; then
        ossutil64 cp -f "${file}" "oss://${OSS_BUCKET}/${OSS_PATH}/$(basename ${file})"
        log "Uploaded to OSS: oss://${OSS_BUCKET}/${OSS_PATH}/$(basename ${file})"
    elif command -v aws &>/dev/null; then
        aws s3 cp "${file}" "s3://${OSS_BUCKET}/${OSS_PATH}/$(basename ${file})"
        log "Uploaded to S3: s3://${OSS_BUCKET}/${OSS_PATH}/$(basename ${file})"
    else
        log "WARNING: No cloud CLI (ossutil/aws) found, skipping upload."
    fi
}

# --- Main ---
log "=== Starting database backup ==="

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/agent_db_${DATE}.sql.gz"

mkdir -p "${BACKUP_DIR}"

# Export database
if command -v pg_dump &>/dev/null; then
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_FILE}"
elif command -v docker &>/dev/null; then
    docker exec agent-postgres pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_FILE}"
else
    log "ERROR: Neither pg_dump nor docker found!"
    exit 1
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
log "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Upload to cloud
upload_to_oss "${BACKUP_FILE}"

# Cleanup old backups
cleanup_old_backups

log "=== Backup completed successfully ==="
