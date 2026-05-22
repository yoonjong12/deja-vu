---
name: dream
description: "Collaborative memory consolidation for deja-vu. Compresses session transcripts via parallel Haiku subagents, then presents draft to user for confirmation before saving. Triggered automatically after compaction or manually."
tags: [memory, consolidation, haiku, parallel, collaborative]
---

# Dream — Collaborative Memory Consolidation

Compress session transcripts into persistent memory through user collaboration. 5 phases: ORIENT → GATHER SIGNAL → CONSOLIDATE → PRESENT & CONFIRM → SAVE.

**Trigger**: Automatically via PostCompact "DREAM NOW" directive, or manually via `/deja-vu dream`.

**Runtime data**: `~/.deja-vu/{slug}/` (resolved by `scripts/resolve-project.sh`).

## Safety

Before first run on a project, back up existing memory:

```bash
slug=$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-project.sh")
cp -r ~/.deja-vu/$slug/memory ~/.deja-vu/$slug/memory.bak.$(date +%s)
```

## Phase 1: ORIENT

Read current memory state to understand what is already known.

1. Resolve project slug:
   ```bash
   slug=$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-project.sh")
   ```

2. Read existing memory index (if any):
   ```
   Read ~/.deja-vu/$slug/memory/MEMORY.md
   ```

3. Read project summary (if any):
   ```
   Read ~/.deja-vu/$slug/project-summary.md
   ```

4. Find session JSONL to process:
   - If `pending-session.json` exists (auto-triggered): use `jsonl_path` from it
   - If manual trigger: find most recent JSONL at `~/.claude/projects/{encoded-cwd}/*.jsonl` where encoding = `cwd.replace("/", "-")`

**Output**: Session JSONL path, existing memory topics, current project summary.

## Phase 2: GATHER SIGNAL

Spawn parallel Haiku subagents to compress the full session JSONL. Each subagent scans an overlapping chunk for signal types.

### JSONL partitioning

Session JSONLs from auto-compaction can be large (200K token conversations). Split into overlapping chunks:

1. Read file size. Divide into N chunks (2-4 depending on size) by byte/line count.
2. Each chunk overlaps with neighbors by ~10% — boundary conversations appear in both chunks.
3. Assign one subagent per chunk.

### Signal types

- **Corrections**: User correcting assistant ("no", "not that", "don't", "wrong")
- **Preferences**: User expressing how they want things done ("always", "never", "I prefer")
- **Decisions**: Architectural or design choices with rationale
- **Patterns**: Recurring workflows, tools, or conventions
- **Key context**: Project goals, deadlines, team structure, external dependencies
- **Artifacts**: Structured content (tables, specs, lists) user created or referenced

### Spawning pattern

For each chunk, spawn a Haiku subagent:

```
Agent(
    description="Scan session chunk N for memory signals",
    model="haiku",
    run_in_background=true,
    prompt="""
    Read the session transcript at: {jsonl_path}
    Read lines {start_line} to {end_line} only.

    Extract ONLY these signal types:
    1. CORRECTIONS — user correcting assistant behavior
    2. PREFERENCES — user expressing how they want things done
    3. DECISIONS — architectural/design choices with rationale
    4. PATTERNS — recurring workflows or conventions
    5. KEY CONTEXT — project goals, deadlines, team info
    6. ARTIFACTS — tables, specs, structured content the user created

    For each signal found, output:
    - type: (correction|preference|decision|pattern|context|artifact)
    - quote: exact user message (truncated to 200 chars)
    - summary: one-line distillation
    - topic: suggested topic slug (kebab-case)

    Output as a JSON array. If no signals found, output [].
    Be SELECTIVE — only extract signals useful across sessions.
    Do not extract: routine Q&A, code already committed, transient debugging.
    """
)
```

Wait for all subagents to complete. Collect their JSON arrays.

### Failure handling

- Partial failure (some subagents return empty/error): continue with successful results.
- Total failure (all subagents fail): skip dream. Do NOT update memory or `.last-dream`. Dream retries on next compaction/session.

**Output**: Merged list of signals with type, quote, summary, topic.

## Phase 3: CONSOLIDATE

Merge extracted signals with existing memory. Prepare draft for user review.

### 3a: Deduplicate overlap signals

Signals from overlapping chunk boundaries may appear twice. Compare summaries — if two signals from adjacent chunks have near-identical summaries, keep one.

### 3b: Session recap draft

From deduplicated signals, build a session recap with checkboxes:

```markdown
# Session Recap (auto-extracted)
- [x] {signal summary 1}
- [x] {signal summary 2}
- [ ] {signal summary 3 — suggested discard}
```

Default: all signals checked. Uncheck signals that seem low-value or redundant with existing memory.

### 3c: Memory diff draft

Compare signals against existing memory topics. Produce diffs:

```markdown
# Memory Changes
+ ADD: {new topic or new entry in existing topic}
~ UPDATE: {existing entry being revised by newer signal}
- REMOVE: {entry contradicted or superseded}
```

### 3d: Project summary update

If KEY CONTEXT signals exist, draft updated project-summary.md (keep under 20 lines).

**Output**: Draft ready for user presentation.

## Phase 4: PRESENT & CONFIRM

Present the consolidated draft to the user for review. Memory is NEVER saved without user confirmation.

### Presentation format

Show the user:

```
# Previous Session Recap
- [x] item 1
- [x] item 2
- [ ] item 3 (suggested discard)

# Memory Changes
+ ADD: new-topic — "description"
~ UPDATE: existing-topic — "revised content"
- REMOVE: (none)
```

### User interaction

```
AskUserQuestion:
  question: "Dream draft ready. Confirm or edit?"
  header: "Dream"
  options:
    - label: "A. Confirm"
      description: "Save memory as shown above"
    - label: "B. Edit"
      description: "Provide corrections (free text)"
```

If user selects B: read their edits, apply changes to the draft, re-present. Loop until user confirms.

**Output**: User-approved memory content.

## Phase 5: SAVE

Write approved memory to disk.

### 5a: Topic memory files

For each approved signal grouped by topic, write to `~/.deja-vu/{slug}/memory/{topic-slug}.md`:

```markdown
---
name: {topic-slug}
description: "{one-line description}"
type: {feedback|project|reference|user}
updated: {YYYY-MM-DD}
---

- {signal summary 1}
- {signal summary 2}
```

Type mapping: correction/preference → feedback, decision/context → project, pattern → reference, artifact → reference.

For artifacts that need verbatim preservation, write to `memory/artifacts/{name}.md`:

```markdown
---
name: {artifact-slug}
description: "{what this is}"
source_session: {YYYY-MM-DD}
preserved: true
---

{original content verbatim}
```

### 5b: Project summary

If updated in draft, write new `project-summary.md`. Keep under 20 lines.

### 5c: Rebuild MEMORY.md index

Each entry is one line under ~150 characters.

**HARD LIMIT: MEMORY.md must not exceed 200 lines.** If it would, prioritize:
1. Recent signals over old
2. Corrections/preferences over context
3. Remove least-referenced topics

### 5d: Cleanup and timestamps

```bash
date +%s > ~/.deja-vu/$slug/.last-dream
rm -f ~/.deja-vu/$slug/.dream-pending
rm -f ~/.deja-vu/$slug/pending-session.json
```

### 5e: Verify

```bash
wc -l ~/.deja-vu/$slug/memory/MEMORY.md
```

If > 200 lines, prune further before completing.
