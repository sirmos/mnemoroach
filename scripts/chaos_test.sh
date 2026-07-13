#!/usr/bin/env bash
#
# scripts/chaos_test.sh
#
# This script stages the main demo moment for the video: start a
# task, kill a node while it is mid step, then show the task
# resuming on another node with no lost work.
#
# It assumes a local multi node CockroachDB cluster started with
# docker-compose.local.yml and initialized with
# scripts/init_local_cluster.sh, and that COCKROACH_URL points at
# one of the nodes.
#
# Usage:
#   ./scripts/chaos_test.sh <task_id>

set -euo pipefail

TASK_ID="${1:-$(python3 -c 'import uuid; print(uuid.uuid4())')}"

echo "starting task $TASK_ID"
python -m scripts.run_task "$TASK_ID" &
TASK_PID=$!

sleep 2

echo "task is running, now killing node 2 to simulate a real crash"
docker kill roach2
# for a softer, graceful demo instead of a hard crash, you could use:
#   cockroach node decommission 2 --insecure --host=localhost:26257
# but that needs the cockroach binary installed on this machine,
# not just inside the containers, and a clean decommission is a
# less honest test of surviving an actual failure anyway.

sleep 2

echo "node 2 is down, checking that the task is still making progress"
python -c "
from memory.store import load_task_state
import sys
state = load_task_state(sys.argv[1])
print('current task state:', state)
" "$TASK_ID"

wait $TASK_PID

echo "task finished. checking final state"
python -c "
from memory.store import load_task_state
import sys
state = load_task_state(sys.argv[1])
print('final task state:', state)
" "$TASK_ID"

echo "done. task_state above should show status done, with no gap in the steps."
echo ""
echo "roach2 is still stopped. bring it back before running this again:"
echo "  docker compose -f docker-compose.local.yml start roach2"