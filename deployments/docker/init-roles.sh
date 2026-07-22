#!/bin/bash

set -euo pipefail

: "${ASILA_DB_APP_PASSWORD:?ASILA_DB_APP_PASSWORD is required}"
: "${ASILA_DB_MIGRATOR_PASSWORD:?ASILA_DB_MIGRATOR_PASSWORD is required}"

psql \
  --set ON_ERROR_STOP=1 \
  --username "${POSTGRES_USER}" \
  --dbname "${POSTGRES_DB}" \
  --set "database_name=${POSTGRES_DB}" \
  --set "app_password=${ASILA_DB_APP_PASSWORD}" \
  --set "migrator_password=${ASILA_DB_MIGRATOR_PASSWORD}" \
  --file /docker-entrypoint-initdb.d/roles.sql.template
