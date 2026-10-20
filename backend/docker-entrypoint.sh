#!/bin/sh
# Entry point del contenedor backend (C-01).
# Aplica las migraciones (R6: siempre reversibles) y luego ejecuta el comando.
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "==> Aplicando migraciones (alembic upgrade head)"
  alembic upgrade head
fi

exec "$@"
