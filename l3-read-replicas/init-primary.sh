#!/bin/bash
set -e

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replicator_password';
EOSQL

# Add replication entry to pg_hba.conf
echo "host replication dbuser db-replica md5" >> "$PGDATA/pg_hba.conf"
echo "host replication dbuser 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
