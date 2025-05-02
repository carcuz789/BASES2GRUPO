#!/bin/bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGUSER=admin
export PGDATABASE=postgres
export WALG_DELTA_MAX_STEPS=5
export WALG_USE_COPY_COMPOSER=true

# Obtener el nombre del último backup completo
LAST_FULL_BACKUP=$(wal-g backup-list --pretty | grep -v incremental_from | tail -n 1 | awk '{print $1}')
if [ -z "$LAST_FULL_BACKUP" ]; then
    echo "No se encontró un backup completo, realizando backup completo"
    wal-g backup-push /var/lib/postgresql/data --full
else
    echo "Realizando backup incremental desde $LAST_FULL_BACKUP"
    wal-g backup-push /var/lib/postgresql/data --delta-from-name "$LAST_FULL_BACKUP"
fi