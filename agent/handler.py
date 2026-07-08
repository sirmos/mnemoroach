"""
agent/handler.py

The Lambda entry point. Lambda calls lambda_handler on every
invocation, we pull the task details out of the event, and hand
off to the same run_task function used everywhere else. Nothing
Lambda specific lives in the agent logic itself, so it is easy to
test locally without deploying anything.

Expected event shape:
{
  "agent_id": "...",
  "task_id": "...",       optional, a new one is made if missing
  "prompt": "..."
}
"""

import json

from agent.loop import run_task


def lambda_handler(event, context):
    if isinstance(event, str):
        event = json.loads(event)

    agent_id = event["agent_id"]
    task_id = event.get("task_id")
    prompt = event["prompt"]

    result = run_task(agent_id, task_id, prompt)

    return {
        "statusCode": 200,
        "body": json.dumps({"result": result}),
    }