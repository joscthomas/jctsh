#!/bin/bash
# CARD-0362 item 2: daily pg_dump backup for data-pipeline's TimescaleDB.
#
# Custom-format dump (pg_restore-compatible, more compact than plain SQL) via
# `docker exec` into timescaledb's own pg_dump binary -- runs inside the
# container so it authenticates the same way any other in-container client
# does (local Unix socket, the jctsh role already provisioned by
# init/schema.sql), no separate credential needed on the host side. Output is
# redirected on the HOST side -- `docker exec`'s stdout is a normal pipe, so
# no extra bind mount into the container is needed for this.
#
# Local-only, matching timescaledb-design.md section 7's own explicit
# accepted-limitation framing: this covers "the container/data directory got
# corrupted," not "the M8 itself is lost." Real off-host backup is separate,
# not-yet-scoped future work (CARD-0362's own item list).
set -euo pipefail

BACKUP_DIR="$HOME/data-pipeline-app/backups"
RETENTION_DAYS=14
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$BACKUP_DIR/jctsh-$TS.dump"

mkdir -p "$BACKUP_DIR"

docker exec data-pipeline-timescaledb pg_dump -U jctsh -Fc jctsh > "$OUT"

# Keep N *days*, not N *files* -- a quiet period or a bad early dump
# shouldn't push good recent dumps out of a fixed-count window the way a
# keep-last-N-files rule would.
find "$BACKUP_DIR" -name 'jctsh-*.dump' -mtime "+$RETENTION_DAYS" -delete

echo "Backup complete: $OUT ($(du -h "$OUT" | cut -f1))"
