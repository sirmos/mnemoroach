"""
memory/store.py

This is the memory layer for the agent. It talks to CockroachDB
directly. No ORM, so it stays easy to read and easy to explain in
a video.

Three jobs live here:
  1. Writing and recalling memories (with embeddings for search)
  2. Saving and loading task state, so a crashed agent can resume
  3. Time travel: looking at what the agent knew in the past, and
     rolling back a memory that turned out to be wrong
"""

import os
import json
import uuid
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()


def _vector_literal(embedding):
    """
    psycopg does not know how to adapt a plain Python list into
    CockroachDB's VECTOR type on its own, it treats it like a
    regular array instead. So we format it into the text form
    CockroachDB expects, for example "[0.1,0.2,0.3]", and cast it
    explicitly in the SQL itself with ::VECTOR.

    Returns None untouched, so optional embeddings still work.
    """
    if embedding is None:
        return None
    if isinstance(embedding, str):
        return embedding
    return "[" + ",".join(str(x) for x in embedding) + "]"


def get_connection():
    """
    Open a connection to CockroachDB using the connection string
    from the environment. Keeping this in one place makes it easy
    to swap in a pooled connection later without touching the rest
    of the code.
    """
    conn_string = os.environ["COCKROACH_URL"]
    return psycopg.connect(conn_string, row_factory=dict_row)


def write_memory(agent_id, kind, content, embedding=None, metadata=None):
    """
    Store a new memory and write its audit entry in the same
    transaction. If either write fails, both are rolled back, so
    the audit log can never drift from what actually happened.
    """
    metadata = metadata or {}
    memory_id = str(uuid.uuid4())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memories (memory_id, agent_id, kind, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s::VECTOR, %s)
                """,
                (memory_id, agent_id, kind, content, _vector_literal(embedding), json.dumps(metadata)),
            )
            cur.execute(
                """
                INSERT INTO memory_audit (memory_id, agent_id, action, actor, reason)
                VALUES (%s, %s, 'create', 'agent', %s)
                """,
                (memory_id, agent_id, f"stored new {kind} memory"),
            )
        conn.commit()

    return memory_id


def recall(agent_id, query_embedding, kind=None, limit=5):
    """
    Find the memories closest to a query embedding. This is the
    agent's semantic search over its own memory, backed by
    CockroachDB's distributed vector index.
    """
    query_vector = _vector_literal(query_embedding)
    with get_connection() as conn:
        with conn.cursor() as cur:
            if kind:
                cur.execute(
                    """
                    SELECT memory_id, kind, content, metadata, created_at
                    FROM memories
                    WHERE agent_id = %s AND kind = %s
                    ORDER BY embedding <-> %s::VECTOR
                    LIMIT %s
                    """,
                    (agent_id, kind, query_vector, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT memory_id, kind, content, metadata, created_at
                    FROM memories
                    WHERE agent_id = %s
                    ORDER BY embedding <-> %s::VECTOR
                    LIMIT %s
                    """,
                    (agent_id, query_vector, limit),
                )
            return cur.fetchall()


def save_task_state(task_id, agent_id, status, step, state):
    """
    Save the agent's progress on a task. Called after every
    meaningful step, not just at the end, so a crash never loses
    more than one step of work.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPSERT INTO task_state (task_id, agent_id, status, step, state, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                """,
                (task_id, agent_id, status, step, json.dumps(state)),
            )
        conn.commit()


def load_task_state(task_id):
    """
    Load the last known state of a task. This is what a resumed
    agent calls first after a crash or a failover to another node.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM task_state WHERE task_id = %s",
                (task_id,),
            )
            return cur.fetchone()


def memory_as_of(agent_id, timestamp):
    """
    Time travel. Returns what the agent's memory looked like at a
    past point in time, using CockroachDB's AS OF SYSTEM TIME. This
    answers the question: what did the agent know, and when did it
    know it.

    timestamp should be an ISO 8601 string, for example
    "2026-07-01T10:00:00Z".
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT memory_id, kind, content, metadata, created_at
                FROM memories AS OF SYSTEM TIME %s
                WHERE agent_id = %s
                ORDER BY created_at
                """,
                (timestamp, agent_id),
            )
            return cur.fetchall()


def rollback_memory(memory_id, agent_id, as_of_timestamp, reason):
    """
    Roll a single memory back to how it looked at a past point in
    time. Used when a memory turns out to be wrong or was written
    by a bad prompt injection.

    This does not delete history. It reads the old value with
    AS OF SYSTEM TIME, writes it back as the current value, and
    logs the rollback in the audit table so there is a clear
    record of what changed and why.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, embedding, metadata
                FROM memories AS OF SYSTEM TIME %s
                WHERE memory_id = %s
                """,
                (as_of_timestamp, memory_id),
            )
            old = cur.fetchone()
            if old is None:
                raise ValueError("no memory found at that point in time")

            cur.execute(
                """
                UPDATE memories
                SET content = %s, embedding = %s::VECTOR, metadata = %s, updated_at = now()
                WHERE memory_id = %s
                """,
                (old["content"], _vector_literal(old["embedding"]), old["metadata"], memory_id),
            )
            cur.execute(
                """
                INSERT INTO memory_audit (memory_id, agent_id, action, actor, reason)
                VALUES (%s, %s, 'rollback', 'operator', %s)
                """,
                (memory_id, agent_id, reason),
            )
        conn.commit()

    return old