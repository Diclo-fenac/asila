FROM pgvector/pgvector:pg16

COPY --chmod=0755 docker/init-roles.sh /docker-entrypoint-initdb.d/10-asila-roles.sh
COPY docker/roles.sql.template /docker-entrypoint-initdb.d/roles.sql.template
