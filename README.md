# deja-vu

> Selective context preservation across Claude Code compaction — remember what matters, not everything.
> Inspired by [claude-brain](https://github.com/mikeadolan/claude-brain) (MIT).

## What

Claude Code auto-compacts at ~200K tokens. Context lost. deja-vu preserves critical signals across compaction via file-based markdown storage + Haiku subagent compression.

- **claude-brain**: store everything (69K messages, 1GB SQLite).
- **deja-vu**: store signals only. Corrections, preferences, decisions, patterns — not full turns.

All data local under `~/.deja-vu/{slug}/`. No SQLite, no network calls, no external deps.

## When

- Long sessions hitting auto-compact regularly.
- Need decision history / progress state to survive compaction.
- Want on-demand search through past session transcripts.

Short ad-hoc tasks → skip.

## Install

```
/plugin marketplace add yoonjong12/deja-vu
/plugin install deja-vu@deja-vu
```

## Prerequisites

**Claude Code** required.

**Python 3** required (hooks run as Python scripts).

No other dependencies.

## Quick start

**Automatic** (on compaction):

```
[Session A] 200K consumed → auto-compact triggers
  ↓
PreCompact hook saves session JSONL path
  ↓
PostCompact hook injects memory + "DREAM NOW" directive
  ↓
Agent runs /deja-vu dream → Haiku subagents compress → you confirm → memory + digest saved
```

**Manual**:

```
/deja-vu dream              # consolidate current session into memory
/deja-vu recall <query>     # search past session transcripts
```

## Concepts

| Concept | Meaning |
|---------|---------|
| **Hooks** | Python scripts fired on Claude Code events. File I/O only, < 1s. No intelligence here. |
| **Dream** | 5-phase memory consolidation. Haiku subagents compress session → orchestrator presents draft → you confirm/edit → memory + digest saved. |
| **Recall** | On-demand transcript search. Digest-filtered when available, full-scan fallback otherwise. Read-only. |
| **Memory** | Markdown files under `~/.deja-vu/{slug}/memory/`. project-summary.md + MEMORY.md index + topic files + artifacts. |
| **Digest** | Per-session summary card under `~/.deja-vu/{slug}/digests/`. Contains keywords, topics, summary, key turn line numbers. Generated as a Dream byproduct — no extra LLM calls. |
| **Slug** | Project identifier from `git remote` → `owner-repo`, fallback to path encoding. |

## Hooks

| Event | Hook | Does |
|-------|------|------|
| PreCompact | `pre-compact.py` | Record session JSONL path to `pending-session.json` |
| PostCompact | `post-compact.py` | Inject existing memory + "DREAM NOW" directive |
| SessionStart | `session-start.py` | Load memory context. Hint dream when overdue (>24h + 5 sessions). |

All hooks: stdout = valid JSON only. Failures → `{}` (silent). No network calls.

## Workflow

```
PreCompact → save JSONL path
    ↓
PostCompact → inject memory + DREAM NOW
    ↓
Dream: ORIENT → GATHER SIGNAL → CONSOLIDATE → PRESENT & CONFIRM → SAVE (memory + digest)
    ↓
SessionStart → load memory on next session
```

| Phase | Does |
|-------|------|
| ORIENT | Read existing memory, find session JSONL |
| GATHER SIGNAL | Parallel Haiku subagents scan overlapping chunks for 6 signal types |
| CONSOLIDATE | Dedup, build session recap checkboxes + memory diffs |
| PRESENT & CONFIRM | Show draft — you confirm or edit. Never auto-saves. |
| SAVE | Write topic files, rebuild MEMORY.md (≤200 lines), generate digest, cleanup |

## How Recall Works

Recall uses a two-stage search when digests are available:

```
/deja-vu recall "auth bug fix"
    ↓
Stage 1: Scan digest frontmatter (keywords + topics) → filter to relevant sessions
    ↓
Stage 2: Haiku subagent searches only matched session JSONLs, guided by digest key turns
    ↓
Present exact matches with surrounding context
```

When no digests exist (first use or pre-0.2.0 data), falls back to full JSONL scan.

## Storage

```
~/.deja-vu/{slug}/
├── project-summary.md          # project overview (≤20 lines)
├── memory/
│   ├── MEMORY.md               # index (≤200 lines)
│   ├── {topic-slug}.md         # topic memory files
│   └── artifacts/{name}.md     # preserved verbatim content
├── digests/                    # per-session summary cards (v0.2.0+)
│   ├── 2026-05-26-abc123.md
│   └── 2026-05-27-def456.md
├── pending-session.json        # ephemeral (pre-compact → dream)
├── .last-dream                 # epoch timestamp
└── .dream-pending              # flag file
```

## License

MIT
