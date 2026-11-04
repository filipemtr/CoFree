#!/bin/sh
set -eu
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then echo 'Uso: sh infrastructure/scripts/restore.sh backups/arquivo.dump'; exit 1; fi
cat "$1" | docker compose exec -T postgres pg_restore -U cofree -d cofree --clean --if-exists --no-owner
printf 'Restauração concluída; confira registros e reinicie os serviços.\n'
