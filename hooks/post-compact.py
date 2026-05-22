#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)


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


def main():
    sys.stdin.read()

    slug = resolve_slug()
    if not slug:
        print(json.dumps({}))
        return

    project_dir = os.path.join(Path.home(), ".deja-vu", slug)
    sections = []

    project_summary = read_file(os.path.join(project_dir, "project-summary.md"))
    if project_summary:
        sections.append("## Project Summary\n" + project_summary)

    memory_md = read_file(os.path.join(project_dir, "memory", "MEMORY.md"))
    if memory_md:
        sections.append("## Memory Index\n" + memory_md)

    pending_path = os.path.join(project_dir, "pending-session.json")
    if os.path.exists(pending_path):
        try:
            with open(pending_path, "r") as f:
                pending = json.load(f)
            jsonl_path = pending.get("jsonl_path", "")
            if jsonl_path and os.path.exists(jsonl_path):
                sections.append(
                    "## DREAM NOW — Mandatory\n"
                    "Auto-compaction detected. A session was just compacted.\n"
                    "Run `/deja-vu dream` IMMEDIATELY before doing anything else.\n"
                    f"Session JSONL: `{jsonl_path}`\n"
                    "This will compress the previous session into memory with your confirmation."
                )
        except (json.JSONDecodeError, OSError):
            pass

    if not sections:
        print(json.dumps({}))
        return

    context = "[deja-vu] Post-compaction context:\n\n" + "\n\n".join(sections)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostCompact",
                    "additionalContext": context,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
