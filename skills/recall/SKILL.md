---
name: recall
description: "Search past session transcripts for original content. Spawns parallel Haiku subagents to grep through raw JSONL files. Use when compressed memory isn't enough — find exact tables, code, phrasing from past sessions."
tags: [search, retrieval, haiku, parallel]
---

# Recall — Session Transcript Search

Search past session transcripts for original content. Complementary to Dream (compressed memory): Recall retrieves exact original content from raw JSONL files.

**Usage**: `/deja-vu recall <search query>`

**Examples**:
- `/deja-vu recall "goals 1-4 table"` — find a specific table from a past session
- `/deja-vu recall "architecture decision"` — find discussion about a design choice
- `/deja-vu recall "error message"` — find when a specific error was discussed

**Read-only**: Recall does NOT modify memory. It only searches and presents.

## Procedure

### 1. Discover session JSONL files

```bash
slug=$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-project.sh")
cwd=$(pwd)
encoded=$(echo "$cwd" | sed 's|/|-|g')
ls -t ~/.claude/projects/$encoded/*.jsonl
```

List all session JSONLs, sorted by recency.

### 2. Spawn search subagent

Spawn a Haiku subagent with the JSONL file paths and query:

```
Agent(
    description="Search session transcripts for: {query}",
    model="haiku",
    run_in_background=true,
    prompt="""
    Search the session transcripts for content matching: "{query}"

    Session JSONL files (most recent first):
    {list of jsonl_paths}

    For each match found:
    1. Extract the matching turn (user or assistant message)
    2. Include 1 turn before and 1 turn after for context
    3. Note the approximate position (early/middle/late in session)
    4. Note which session file the match came from

    Output as JSON array:
    [
      {
        "session_file": "filename",
        "match": "the matching content (up to 500 chars)",
        "context_before": "previous turn summary",
        "context_after": "next turn summary",
        "role": "user|assistant",
        "position": "early|middle|late"
      }
    ]

    If no matches, output [].
    Prioritize exact matches over semantic similarity.
    """
)
```

### 3. Present results

After subagent completes, present with session date and context:

```markdown
## Recall Results for "{query}"

### Session: 2026-05-21
**Match** (middle of session, assistant):
> {original content}

**Context**: User asked about X, assistant responded with this table...

### Session: 2026-05-19
**Match** (late in session, user):
> {original content}
```

If no results found across all sessions, report: "No matches found for '{query}'."
