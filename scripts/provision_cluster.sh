#!/usr/bin/env bash
#
# scripts/provision_cluster.sh
#
# Uses the ccloud CLI to create the CockroachDB Cloud cluster this
# project runs on. Multi node on purpose, since the whole point of
# the chaos test is showing the agent survive a node going down.
#
# Every command below is a real, documented ccloud command. Where
# a step needs the Cloud Console or Cloud API instead of the CLI,
# that is called out directly rather than guessed at.
#
# Requires: ccloud CLI installed, and ccloud auth login already run.

set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-mnemoroach}"
REGION_SPEC="${REGION_SPEC:-us-east-1:3}"   # region:nodecount
VCPUS="${VCPUS:-2}"
STORAGE_GIB="${STORAGE_GIB:-50}"

echo "creating dedicated cluster: $CLUSTER_NAME ($REGION_SPEC on AWS)"

ccloud cluster create dedicated "$CLUSTER_NAME" "$REGION_SPEC" \
  --cloud AWS \
  --vcpus "$VCPUS" \
  --storage-gib "$STORAGE_GIB"

echo "cluster creation kicked off. this can take a while to finish provisioning."
echo "check progress with:"
echo "  ccloud cluster list -o json"

echo ""
echo "once the cluster shows CLUSTER_STATE_CREATED, connect to it with:"
echo "  ccloud cluster sql --id <cluster-id>"
echo ""
echo "the first SQL connection will prompt you to create a SQL user."
echo "that user is granted admin by default. after creating it, connect"
echo "and run this to give the agent a lower privileged role instead:"
echo ""
echo "  GRANT SELECT, INSERT, UPDATE, DELETE ON DATABASE mnemoroach TO <agent_user>;"
echo ""
echo "next steps:"
echo "1. run the schema:"
echo "   ccloud cluster sql --id <cluster-id> < db/schema.sql"
echo "2. build the connection string for your .env as COCKROACH_URL."
echo "   the ccloud cluster sql command will show you the connection"
echo "   details, or find them in the Cloud Console under Connect."
echo ""
echo "note on service accounts and MCP tokens:"
echo "CockroachDB Cloud service accounts and API keys are managed"
echo "through the Cloud Console or the Cloud API, not this CLI."
echo "create the agent's service account and API key there, scoped"
echo "to Cluster Developer role on this cluster only, then use that"
echo "key for the MCP server config in mcp.config.json."
echo ""
echo "to check activity on this cluster later (useful for the"
echo "production readiness story in the writeup):"
echo "  ccloud audit list --limit 20 --starting-from <ISO-8601 timestamp>"