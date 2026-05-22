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


def resolve_slug():
    script = os.path.join(PLUGIN_ROOT, "scripts", "resolve-project.sh")
    result = subprocess.run(
        ["bash", script], capture_output=True, text=True, timeout=3
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def find_session_jsonl():
    cwd = os.environ.get("CWD", os.getcwd())
    encoded = cwd.replace("/", "-")
    project_dir = os.path.join(Path.home(), ".claude", "projects", encoded)
    jsonl_files = glob.glob(os.path.join(project_dir, "*.jsonl"))
    if not jsonl_files:
        return None
    return max(jsonl_files, key=os.path.getmtime)


def main():
    sys.stdin.read()

    slug = resolve_slug()
    if not slug:
        print(json.dumps({}))
        return

    jsonl_path = find_session_jsonl()
    if not jsonl_path:
        print(json.dumps({}))
        return

    deja_vu_dir = os.path.join(Path.home(), ".deja-vu", slug)
    os.makedirs(deja_vu_dir, exist_ok=True)

    pending = {"jsonl_path": jsonl_path, "timestamp": time.time()}
    pending_path = os.path.join(deja_vu_dir, "pending-session.json")
    with open(pending_path, "w") as f:
        json.dump(pending, f)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
