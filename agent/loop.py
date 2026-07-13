"""
agent/loop.py

The agent's main loop. This is deliberately hand written instead of
using a managed agent framework, so every read and write to memory
is visible and easy to explain.

The loop works like this:
  1. Check if this task already has state saved. If it does, resume
     from there instead of starting over. This is what makes a node
     failure survivable.
  2. Pull relevant memories for context.
  3. Call the model with that context.
  4. Save progress to task_state after every step.
  5. Store anything worth remembering as a new memory.
"""

import os
import json
import uuid
import boto3

from memory.store import (
    write_memory,
    recall,
    save_task_state,
    load_task_state,
)

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def embed(text):
    """
    Turn text into an embedding using a Bedrock embedding model.
    Kept as its own function so it is easy to swap models later.
    """
    response = bedrock.invoke_model(
        modelId=os.environ.get("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"),
        body=json.dumps({"inputText": text}),
    )
    payload = json.loads(response["body"].read())
    return payload["embedding"]


def call_model(prompt, context_memories):
    """
    Call the reasoning model with the task prompt plus whatever
    memories we pulled as context.
    """
    context_text = "\n".join(f"- {m['content']}" for m in context_memories)
    full_prompt = (
        f"Relevant memory:\n{context_text}\n\nTask:\n{prompt}"
        if context_memories
        else prompt
    )

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": full_prompt}],
            }
        ),
    )
    payload = json.loads(response["body"].read())
    return payload["content"][0]["text"]


def run_task(agent_id, task_id, prompt):
    """
    Run one step of a task. Safe to call again with the same
    task_id after a crash, since it checks saved state first.
    """
    existing = load_task_state(task_id)

    if existing and existing["status"] == "done":
        return existing["state"]

    if existing:
        print(f"resuming task {task_id} from step: {existing['step']}")
    else:
        task_id = task_id or str(uuid.uuid4())
        save_task_state(task_id, agent_id, "running", "start", {})

    query_embedding = embed(prompt)
    context_memories = recall(agent_id, query_embedding, limit=5)

    save_task_state(task_id, agent_id, "running", "calling_model", {"prompt": prompt})

    result = call_model(prompt, context_memories)

    write_memory(agent_id, "conversation", result, embedding=embed(result))

    save_task_state(task_id, agent_id, "done", "complete", {"result": result})

    return result