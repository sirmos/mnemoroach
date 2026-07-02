# Mnemoroach

Memory for AI agents that does not go down.

Mnemoroach is an agent memory system built on CockroachDB. It stores what an agent knows, keeps working when a node or a whole region fails, and lets you look back in time to see and undo what the agent remembered.

## Why this exists

Most agent memory is a thin wrapper around a vector store. That works until something breaks. If the database node holding an agent's memory goes down, the agent does not slow down, it just stops. And if a bad memory gets written in, by a mistake or by a prompt injection, there is usually no way to tell when it happened or to undo it cleanly.

CockroachDB is built for exactly this problem. It is a distributed database that keeps running when nodes fail, and it keeps history, so you can query what your data looked like in the past. Mnemoroach uses both of these directly, not as an afterthought.

## What it does

- Stores agent memory (facts, task state, conversation, context) with vector embeddings for search
- Keeps working through node and region failures, because the memory lives in CockroachDB, not on one machine
- Saves task progress after every step, so a crashed or interrupted task resumes from where it left off, not from the start
- Lets you query what the agent knew at any point in the past using `AS OF SYSTEM TIME`
- Lets you roll a specific memory back to an earlier version, with a full audit trail of what changed and why

## CockroachDB tools used

- **CockroachDB Cloud Managed MCP Server** — lets Claude Code or Cursor connect directly to the cluster during development, read only by default. Config in `mcp.config.json`.
- **Distributed Vector Indexing** — the `memories` table has a vector column with a distributed index, used for semantic recall in `memory/store.py`.
- **ccloud CLI** — used in `scripts/` for provisioning and for the chaos test, which decommissions a node mid task to show the agent keeps working.

## AWS services used

- **AWS Lambda** — runs the agent loop
- **Amazon Bedrock** — the reasoning model and the embedding model

## Project layout

```
db/                schema.sql, the full CockroachDB schema
memory/store.py     read and write memory, task state, time travel, rollback
agent/loop.py        the agent loop itself, calls Bedrock and memory/store.py
scripts/             chaos test, setup, and helper scripts
mcp.config.json       MCP server config for Claude Code / Cursor
```

## Setup

1. Create a CockroachDB Cloud cluster, or run one locally with `cockroach demo`.
2. Copy `.env.example` to `.env` and fill in your connection string and AWS details.
3. Run the schema:
   ```
   cockroach sql --url "$COCKROACH_URL" < db/schema.sql
   ```
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Run a task:
   ```
   python -m scripts.run_task
   ```

## Running the chaos test

This is the main demo. It starts a task, kills a node while the task is mid step, and shows the task finishing anyway with no lost progress.

```
./scripts/chaos_test.sh
```

Watch the task state print before and after the node goes down. The step count should not skip or reset.

## Time travel and rollback

To see what an agent knew at a past point in time:

```python
from memory.store import memory_as_of
memory_as_of(agent_id, "2026-07-01T10:00:00Z")
```

To roll a specific memory back to how it looked at that time:

```python
from memory.store import rollback_memory
rollback_memory(memory_id, agent_id, "2026-07-01T10:00:00Z", reason="memory was corrupted by a bad input")
```

Every rollback is logged in `memory_audit`, so there is a clear record of what changed.

## License

MIT, see `LICENSE`.
