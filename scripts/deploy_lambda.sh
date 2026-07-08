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
  echo "set COCKROACH_URL first, for example:"
  echo "  export COCKROACH_URL=postgresql://user:pass@host:26257/mnemoroach?sslmode=verify-full"
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