#!/usr/bin/env bash
#
# scripts/init_local_cluster.sh
#
# Run once, after docker compose -f docker-compose.local.yml up -d
# and the containers have had a few seconds to start.

set -euo pipefail

echo "initializing the cluster (tells the 3 nodes to form one cluster)"
docker exec roach1 ./cockroach init --insecure

echo "waiting a moment for the cluster to settle"
sleep 3

echo "creating the mnemoroach database"
docker exec roach1 ./cockroach sql --insecure --execute "CREATE DATABASE IF NOT EXISTS mnemoroach;"

echo "loading the schema"
docker exec -i roach1 ./cockroach sql --insecure --database mnemoroach < db/schema.sql

echo "done. connection string for local .env:"
echo "COCKROACH_URL=postgresql://root@localhost:26257/mnemoroach?sslmode=disable"
echo ""
echo "check the cluster is healthy at http://localhost:8080"