"""
agent/handler.py

The Lambda entry point. Lambda calls lambda_handler on every
invocation, we pull the task details out of the event, and hand
off to the same run_task function used everywhere else. Nothing
Lambda specific lives in the agent logic itself, so it is easy to
test locally without deploying anything.

This function is wired up behind API Gateway (see template.yaml).
API Gateway's proxy integration wraps the actual request body as a
JSON string inside event["body"], it does not pass your JSON
payload as top level keys on event. So we have to unwrap that
first. If this function is ever invoked directly (bypassing API
Gateway, for example via the AWS console's test feature or the CLI),
top level keys are also supported as a fallback.

Expected request body (JSON):
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

    if "body" in event:
        body = event["body"]
        payload = json.loads(body) if isinstance(body, str) else body
    else:
        payload = event

    agent_id = payload["agent_id"]
    task_id = payload.get("task_id")
    prompt = payload["prompt"]

    result = run_task(agent_id, task_id, prompt)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"result": result}),
    }