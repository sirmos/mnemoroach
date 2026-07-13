-- Mnemoroach schema
-- This is the memory layer for the agent. Everything the agent knows
-- lives here, in CockroachDB, so it survives node and region failures.

CREATE TABLE IF NOT EXISTS agents (
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Core memory table. One row per fact, task state, or piece of context
-- the agent has stored. We keep this table simple and let CockroachDB's
-- built in history (AS OF SYSTEM TIME) handle versioning, so we do not
-- need to hand roll our own version column for basic time travel.
CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    kind STRING NOT NULL CHECK (kind IN ('fact', 'task_state', 'context', 'conversation')),
    content STRING NOT NULL,
    -- 1024 matches Amazon Titan Text Embeddings V2's default output size.
    -- Titan V2 can also produce 256 or 512 dimensional embeddings if you
    -- configure it that way, but this project uses the default.
    embedding VECTOR(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Vector index for semantic search over memories.
CREATE VECTOR INDEX IF NOT EXISTS memories_embedding_idx
    ON memories (embedding);

-- Audit log. Every write to memory gets a row here, in the same
-- transaction as the write itself. This is what lets us answer
-- "what did the agent know, and when did it learn it" and lets us
-- prove a rollback actually happened.
CREATE TABLE IF NOT EXISTS memory_audit (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    action STRING NOT NULL CHECK (action IN ('create', 'update', 'delete', 'rollback')),
    actor STRING NOT NULL DEFAULT 'agent',
    reason STRING,
    at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS memory_audit_memory_id_idx ON memory_audit (memory_id);
CREATE INDEX IF NOT EXISTS memory_audit_agent_id_idx ON memory_audit (agent_id);

-- Task state table for long running work. This is what survives a
-- crash mid task. The agent writes progress here as it goes, not
-- just at the end.
CREATE TABLE IF NOT EXISTS task_state (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    status STRING NOT NULL CHECK (status IN ('running', 'paused', 'done', 'failed')),
    step STRING NOT NULL,
    state JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);