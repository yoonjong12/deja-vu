#!/usr/bin/env python3
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
DREAM_INTERVAL = 86400
MIN_SESSIONS_FOR_DREAM = 5


def resolve_slug():
    script = os.path.join(PLUGIN_ROOT, "scripts", "resolve-project.sh")
    result = subprocess.run(
        ["bash", script], capture_output=True, text=True, timeout=3
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def read_file(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read().strip()


def count_session_jsonls():
    cwd = os.environ.get("CWD", os.getcwd())
    encoded = cwd.replace("/", "-")
    project_dir = os.path.join(Path.home(), ".claude", "projects", encoded)
    return len(glob.glob(os.path.join(project_dir, "*.jsonl")))


def check_dream_needed(project_dir):
    last_dream_path = os.path.join(project_dir, ".last-dream")
    if not os.path.exists(last_dream_path):
        return count_session_jsonls() >= MIN_SESSIONS_FOR_DREAM

    try:
        with open(last_dream_path, "r") as f:
            last_epoch = float(f.read().strip())
    except (ValueError, OSError):
        return False

    if time.time() - last_epoch < DREAM_INTERVAL:
        return False

    return count_session_jsonls() >= MIN_SESSIONS_FOR_DREAM


def main():
    sys.stdin.read()

    slug = resolve_slug()
    if not slug:
        print(json.dumps({}))
        return

    project_dir = os.path.join(Path.home(), ".deja-vu", slug)
    if not os.path.isdir(project_dir):
        print(json.dumps({}))
        return

    sections = []

    project_summary = read_file(os.path.join(project_dir, "project-summary.md"))
    if project_summary:
        sections.append("## Project Summary\n" + project_summary)

    memory_md = read_file(os.path.join(project_dir, "memory", "MEMORY.md"))
    if memory_md:
        sections.append("## Memory Index\n" + memory_md)

    if check_dream_needed(project_dir):
        Path(os.path.join(project_dir, ".dream-pending")).touch()
        sections.append(
            "## Dream Consolidation Due\n"
            "Memory consolidation has not run in over 24 hours.\n"
            "Consider running `/deja-vu dream` to consolidate session insights into persistent memory."
        )

    if not sections:
        print(json.dumps({}))
        return

    context = "[deja-vu] Session context loaded:\n\n" + "\n\n".join(sections)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
