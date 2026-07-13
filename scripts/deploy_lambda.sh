#!/usr/bin/env bash
#
# scripts/deploy_lambda.sh
#
# Builds and deploys the agent Lambda using AWS SAM.
#
# The --use-container flag on sam build matters here: psycopg has
# a compiled C extension, and building it on a Mac or Windows
# laptop produces a binary that will not run on Lambda's Linux
# environment. --use-container builds inside a Lambda-like Docker
# image instead, so the compiled extension actually works once
# deployed.
#
# Requires: AWS SAM CLI, Docker running, and AWS credentials
# already configured (aws configure or an assumed role).

set -euo pipefail

if [ -z "${COCKROACH_URL:-}" ]; then
  echo "set COCKROACH_URL first, pointed at the CLOUD cluster, not localhost."
  echo "Lambda cannot reach a cluster running in your Codespace."
  echo ""
  echo "It also needs sslrootcert pointing at the bundled cert path, since"
  echo "Lambda has no ~/.postgresql directory of its own. For example:"
  echo '  export COCKROACH_URL="postgresql://demo_user:PASSWORD@your-cluster-host:26257/mnemoroach?sslmode=verify-full&sslrootcert=/var/task/certs/cockroachdb-ca.crt"'
  exit 1
fi

if [[ "$COCKROACH_URL" != *"sslrootcert=/var/task/certs"* ]]; then
  echo "warning: COCKROACH_URL does not include sslrootcert=/var/task/certs/cockroachdb-ca.crt"
  echo "without it, the Lambda function will fail to connect with a certificate error."
  echo "see certs/README.txt for how to set this up."
  read -p "continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

if [ ! -f "certs/cockroachdb-ca.crt" ]; then
  echo "certs/cockroachdb-ca.crt not found. copy your cluster's CA cert there first:"
  echo "  cp ~/.postgresql/root.crt certs/cockroachdb-ca.crt"
  exit 1
fi

echo "building (this uses a container so the psycopg C extension matches Lambda's runtime)"
sam build --use-container

echo "deploying"
sam deploy \
  --stack-name mnemoroach \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides "CockroachUrl=${COCKROACH_URL}" \
  --resolve-s3 \
  --no-confirm-changeset

echo ""
echo "done. find the invoke URL in the Outputs above, or run:"
echo "  aws cloudformation describe-stacks --stack-name mnemoroach --query \"Stacks[0].Outputs\""