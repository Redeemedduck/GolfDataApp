# Golf Agent — Design Document

**Date:** 2026-02-13
**Status:** Approved
**Approach:** Agent module inside GolfDataApp (Approach 1)

## Summary

An all-in-one golf agent (coaching + analysis + safe data management) built with the Claude Agent SDK in Python. Accessible via three interfaces: terminal CLI, Claude Code slash command, and Streamlit AI Coach page. Uses the existing hybrid SQLite/Supabase data access layer. Read + safe writes only.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Interfaces                      │
│                                                  │
│  Terminal CLI    Claude Code Skill    Streamlit   │
│  (agent/cli.py)  (~/.claude/skills)  (provider)  │
└──────┬──────────────┬──────────────────┬─────────┘
       │              │                  │
       ▼              ▼                  ▼
┌─────────────────────────────────────────────────┐
│              agent/core.py                       │
│                                                  │
│  Claude Agent SDK                                │
│  - System prompt (golf coaching persona)         │
│  - Tool definitions                              │
│  - Conversation session management               │
│  - Streaming responses                           │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              agent/tools.py                      │
│                                                  │
│  Tool functions wrapping golf_db.py              │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              golf_db.py (existing)               │
│              SQLite + Supabase hybrid            │
└─────────────────────────────────────────────────┘
```

**Key principle:** `agent/core.py` is the only file that knows about the Claude Agent SDK. The three interfaces are thin adapters.

## Agent Core (`agent/core.py`)

**System prompt** — a golf-specific coaching persona that knows:
- It's analyzing real practice data from a Uneekor launch monitor
- The Big 3 Impact Laws (Face Angle, Club Path, Strike Quality)
- How to interpret launch monitor metrics (carry, ball speed, smash factor, spin)
- It should be encouraging but honest

**Session management:**
- CLI and skill: single conversation per invocation (no persistence between runs)
- Streamlit: conversation history stored in `st.session_state`

**Streaming:** Agent streams responses for CLI. Streamlit and skill get complete responses.

**Model:** Claude Sonnet 4.5 (fast + capable for coaching).

**Permissions:** SDK permission set to `DEFAULT` — agent can only use explicitly defined tools.

## Tools (`agent/tools.py`)

### Read Tools

| Tool | Wraps | Purpose |
|------|-------|---------|
| `query_shots` | `golf_db.get_shots()` | Fetch shots with filters (club, date range, session) |
| `get_session_list` | `golf_db.get_sessions()` | List sessions with dates and shot counts |
| `get_session_summary` | `golf_db.get_session_stats()` | Per-session aggregates (avg carry, Big 3) |
| `get_club_stats` | `golf_db.get_club_summary()` | Per-club averages and trends |
| `get_big3_metrics` | Computed from shots | Face Angle, Club Path, Strike Quality analysis |
| `get_trends` | Computed from shots | Metric trends over last N sessions |
| `compare_sessions` | Two `get_session_stats` | Side-by-side session comparison |

### Safe Write Tools

| Tool | Wraps | Purpose |
|------|-------|---------|
| `tag_session` | `golf_db.update_shot_metadata()` | Add/update tags on a session |
| `add_session_note` | `golf_db.update_shot_metadata()` | Add text note to a session |
| `batch_rename_sessions` | `golf_db.batch_update_session_names()` | Regenerate display names |

### Explicitly Excluded

- No `delete_session` or `delete_shots`
- No `add_shot` or raw SQL
- No automation triggers (backfill, scrape, sync)
- No Supabase admin operations

Agent can suggest these actions but cannot execute them.

## Interfaces

### A. Terminal CLI (`agent/cli.py`)

- Run with `python -m agent.cli`
- Streaming chat loop
- `--single "<question>"` flag for one-shot mode (used by skill)
- No conversation persistence between runs
- API key from environment via `op run`

### B. Claude Code Skill (`~/.claude/skills/golf/SKILL.md`)

- Slash command: `/golf <question>`
- Invokes `python -m agent.cli --single "<question>"`
- Output returned to Claude Code conversation

### C. Streamlit Provider (`services/ai/providers/claude_provider.py`)

- Registers via `@register_provider` decorator
- `PROVIDER_ID = "claude"`, `DISPLAY_NAME = "Claude Golf Coach"`
- Conversation history in `st.session_state`
- Full response (no streaming) for Streamlit rendering

## Permissions & Safety

- `ANTHROPIC_API_KEY` from environment, never hardcoded
- Agent SDK permissions: `DEFAULT` (no filesystem, shell, or network)
- All writes through `golf_db.py` parameterized SQL
- `update_shot_metadata()` enforces `ALLOWED_UPDATE_FIELDS` allowlist
- No rate limiting needed (personal tool, conversational usage)
- Model: Sonnet 4.5 (~$3/1M input, $15/1M output)

## New Files

| File | Purpose |
|------|---------|
| `agent/__init__.py` | Package init |
| `agent/core.py` | Agent SDK agent with system prompt + tools |
| `agent/tools.py` | Tool definitions wrapping golf_db |
| `agent/cli.py` | Terminal chat interface |
| `services/ai/providers/claude_provider.py` | Streamlit AI Coach provider |
| `~/.claude/skills/golf/SKILL.md` | `/golf` slash command |
| `.env.template` | Add `ANTHROPIC_API_KEY` reference |
