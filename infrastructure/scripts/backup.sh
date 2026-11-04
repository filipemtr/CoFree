#!/bin/sh
set -eu
mkdir -p backups
now=$(date -u +%Y%m%dT%H%M%SZ)
docker compose exec -T postgres pg_dump -U cofree -Fc cofree > "backups/cofree-$now.dump"
echo "Backup criado em backups/cofree-$now.dump (trate como informação sensível)."
