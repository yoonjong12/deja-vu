---
name: recall
description: "Search past session transcripts for original content. Uses digest sidecars for fast filtering, then targeted Haiku subagent scan. Falls back to full scan when no digests exist."
tags: [search, retrieval, haiku, parallel, digest]
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

### 1. Resolve project

```bash
slug=$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-project.sh")
```

### 2. Check for digests

```bash
ls -t ~/.deja-vu/$slug/digests/*.md 2>/dev/null
```

If digest files exist → go to **Step 3a** (filtered search).
If no digest files → go to **Step 3b** (full scan fallback).

### 3a. Filtered search (digest-powered)

Two-stage approach: filter by digest metadata first, then scan only relevant sessions.

**Stage 1: Filter digests by frontmatter**

For each digest file, read only the frontmatter (first ~10 lines). Extract `keywords` and `topics` fields. Match query terms against these fields.

Ranking: count how many query terms appear in `keywords` + `topics`. Higher overlap = higher rank.

Select top K digests where K ≤ 5.

If zero digests match → fall through to **Step 3b** (full scan).

**Stage 2: Targeted Haiku scan**

Spawn a Haiku subagent with the matched digests and their JSONL paths:

```
Agent(
    description="Search session transcripts for: {query}",
    model="haiku",
    run_in_background=true,
    prompt="""
    Search for content matching: "{query}"

    Matched session digests (ranked by relevance):
    {for each matched digest, include: session ID, summary, key turns}

    JSONL files to search (only these):
    {jsonl_path from each matched digest}

    Search strategy:
    1. Read the digest summaries above to understand each session
    2. Use the "Key turns" line numbers as starting points in the JSONL
    3. Read around those line numbers for exact matching content
    4. Also scan broadly within each JSONL for matches the digest may not have captured

    For each match found, output JSON:
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

### 3b. Full scan fallback (no digests)

When no digests exist (pre-0.2.0 data or first sessions before any dream), fall back to full JSONL scan.

```bash
cwd=$(pwd)
encoded=$(echo "$cwd" | sed 's|/|-|g')
ls -t ~/.claude/projects/$encoded/*.jsonl
```

Spawn a Haiku subagent with all JSONL paths:

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

### 4. Present results

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
