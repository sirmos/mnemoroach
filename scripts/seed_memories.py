"""
scripts/seed_memories.py

Loads a handful of realistic memories for the default demo agent,
so the video has something real to show. Without this, the first
run of the agent has nothing in memory and recall just returns
nothing useful, which does not make for a convincing video.

The story here: the agent is helping a team plan and run a
database migration. That gives recall, task_state, and rollback
all something meaningful to work with on camera.

Run once, after the cluster is up and the schema is loaded:
    python -m scripts.seed_memories
"""

from agent.loop import embed
from memory.store import write_memory

AGENT_ID = "00000000-0000-0000-0000-000000000001"

SEED_MEMORIES = [
    ("fact", "The customer runs production on a 3 node CockroachDB cluster in us-east-1."),
    ("fact", "The migration's hard requirement is zero downtime, no exceptions."),
    ("context", "Connection timeouts spike every Tuesday during peak traffic hours, cause still unclear."),
    ("fact", "The customer prefers Slack alerts over email for anything urgent."),
    ("context", "The team agreed to run the migration over a weekend to lower risk."),
    ("fact", "The customer's on call engineer is only available after 9am Eastern."),
]


def main():
    print(f"seeding {len(SEED_MEMORIES)} memories for agent {AGENT_ID}")
    for kind, content in SEED_MEMORIES:
        embedding = embed(content)
        memory_id = write_memory(AGENT_ID, kind, content, embedding=embedding)
        print(f"  stored [{kind}] {content[:60]}...  ({memory_id})")
    print("done")


if __name__ == "__main__":
    main()