"""
scripts/run_task.py

Small command line entry point so the chaos test script can start
a task as a background process.

Usage:
    python -m scripts.run_task <task_id> ["optional prompt text"]
"""

import sys
import uuid

from agent.loop import run_task

DEFAULT_AGENT_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_PROMPT = "Summarize what you know so far and suggest the next step."


def main():
    task_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
    prompt = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PROMPT

    result = run_task(DEFAULT_AGENT_ID, task_id, prompt)
    print("task result:", result)


if __name__ == "__main__":
    main()
