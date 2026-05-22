#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-$(pwd)}"

if remote=$(git -C "$TARGET" remote get-url origin 2>/dev/null); then
    # https://github.com/owner/repo.git → owner-repo
    # git@github.com:owner/repo.git → owner-repo
    slug=$(echo "$remote" | sed 's|\.git$||; s|.*[:/]\([^/]*\)/\([^/]*\)$|\1-\2|')
    echo "$slug"
    exit 0
fi

# Fallback: encode cwd path
# /Users/jay/code/deja-vu → Users-jay-code-deja-vu
slug=$(echo "$TARGET" | sed 's|^/||; s|/|-|g')
echo "$slug"
