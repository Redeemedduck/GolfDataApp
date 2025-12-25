# Repository Branch Analysis

## All Branches Found

### Local Branches:
1. `claude/fix-supabase-gemini-issues-PXRya` (created by me today - should probably be deleted)
2. `claude/unified-ai-docker-integration` (temp branch I created - should probably be deleted)
3. `claude/unified-ai-docker-PXRya` (currently checked out)
4. `docker`
5. `main`

### Remote Branches:
1. `origin/main`
2. `origin/docker`
3. `origin/claude/integrate-claude-agents-PUqOS` ⭐ **KEY BRANCH**
4. `origin/claude/mcp-coaching-setup-HaPyc`
5. `origin/claude/fix-supabase-gemini-issues-PXRya`
6. `origin/claude/unified-ai-docker-PXRya`
7. `origin/nextjs-web-app`

---

## Branch Comparison Summary

### 1. **main** Branch
**Purpose:** Production-ready base with cloud pipeline

**Key Features:**
- Local-first hybrid: SQLite + Supabase + BigQuery
- **Gemini AI in SCRIPTS only** (not in Streamlit app)
- MCP Control Plane integration
- Cloud pipeline: Supabase → BigQuery → Gemini analysis
- Scripts: `gemini_analysis.py`, `vertex_ai_analysis.py`
- **NO AI in Streamlit app** - just dashboard, shot viewer, data management
- **NO Docker**
- **NO Claude**

**Database Flow:**
```
Uneekor API → SQLite → Supabase → BigQuery → Gemini (scripts only)
                                            ↓
                                     MCP Control Plane
```

---

### 2. **docker** Branch
**Purpose:** Docker-containerized version of main + Claude AI

**Key Features:**
- Everything from main, PLUS:
- **Docker/OrbStack containerization**
- **Claude AI in Streamlit app** (AI Coach tab)
- Multi-stage Dockerfile
- docker-compose with volumes
- Volume mounts: `./data/`, `./media/`, `./logs/`
- **NO Gemini in app** (still only in scripts)
- **Claude ONLY in app**

**What's Added:**
- Dockerfile
- docker-compose.yml
- docker-quickstart.sh
- Claude AI Coach tab (Opus/Sonnet/Haiku models)
- Comprehensive Docker documentation

**Database Flow:**
```
[Docker Container]
  Uneekor API → SQLite → Supabase → BigQuery → Gemini (scripts)
                   ↓                              ↓
            Volume mounted                 MCP Control Plane

  Streamlit App → Claude AI (in-app coaching)
```

---

### 3. **claude/integrate-claude-agents-PUqOS** Branch ⭐
**Purpose:** DUAL AI SYSTEM - Both Claude AND Gemini

**Key Features:**
- **BOTH Claude AND Gemini** in scripts
- **Claude AI in Streamlit app** (AI Coach tab)
- Multi-agent comparison tools
- Scripts for both:
  - `scripts/claude_analysis.py` (NEW)
  - `scripts/gemini_analysis.py`
  - `scripts/compare_ai_analysis.py` (NEW - compares both)
- **NO Docker** (based on main, not docker)
- Local SQLite + Supabase + BigQuery

**What's Unique:**
- Dual AI analysis pipeline
- Comparison tools to see Claude vs Gemini insights side-by-side
- Interactive chat mode in scripts
- Multi-model support for Claude (opus/sonnet/haiku flags)

**Database Flow:**
```
Uneekor API → SQLite → Supabase → BigQuery ┬→ Claude (scripts)
                                             └→ Gemini (scripts)
                                                    ↓
Streamlit App → Claude AI (in-app)      Compare AI (scripts)
```

---

### 4. **claude/mcp-coaching-setup-HaPyc** Branch
**Purpose:** Appears to be a copy of docker branch

**Key Features:**
- Same CLAUDE.md as docker branch
- Likely Docker + MCP focused
- **Claude AI in app** (inherited from docker)
- Possibly focuses on MCP integration

---

### 5. **nextjs-web-app** Branch
**Purpose:** Unknown - different tech stack?

**Key Features:**
- No CLAUDE.md found
- Likely a Next.js rewrite attempt
- Probably experimental/separate project

---

## Common Elements Across All Branches

### Core Codebase (All Branches):
1. **golf_scraper.py** - Uneekor API client
2. **golf_db.py** - SQLite + Supabase hybrid database
3. **app.py** - Streamlit UI
4. **Supabase schema** - 30 fields per shot
5. **BigQuery integration** - Cloud data warehouse
6. **scripts/** directory - Analysis tools

### Database Schema (All Branches):
- SQLite local-first
- Supabase cloud backup
- BigQuery analytics
- 30 shot metrics (ball speed, spin, angles, impact location, etc.)
- Denver altitude context

### Data Pipeline (All Branches):
```
Uneekor API → SQLite (local) → Supabase (cloud) → BigQuery (warehouse)
```

---

## Key Differences Matrix

| Feature | main | docker | integrate-claude-agents | mcp-coaching |
|---------|------|--------|------------------------|--------------|
| **Docker** | ❌ | ✅ | ❌ | ✅ (likely) |
| **Claude in Scripts** | ❌ | ❌ | ✅ | ❌ |
| **Gemini in Scripts** | ✅ | ✅ | ✅ | ✅ |
| **Claude in App** | ❌ | ✅ | ✅ | ✅ (likely) |
| **Gemini in App** | ❌ | ❌ | ❌ | ❌ |
| **Multi-Agent Compare** | ❌ | ❌ | ✅ | ❌ |
| **MCP Control Plane** | ✅ | ✅ | ? | ✅ |
| **Supabase** | ✅ | ✅ | ✅ | ✅ |
| **BigQuery** | ✅ | ✅ | ✅ | ✅ |

---

## What Each Branch is Best For

### Use **main** if you want:
- Simplest setup (no Docker)
- Gemini-only analysis via scripts
- MCP Control Plane access
- Production-ready base

### Use **docker** if you want:
- Easy deployment (Docker/OrbStack)
- Claude AI coaching in Streamlit app
- Production containerization
- Same data pipeline as main

### Use **integrate-claude-agents** if you want:
- Both Claude AND Gemini analysis
- Compare insights from multiple AI models
- Most comprehensive AI capabilities
- Non-Docker setup

### Use **mcp-coaching** if you want:
- Docker + MCP focus
- Appears to be docker branch variant

---

## The Branch You Asked About

Based on your description of a "production ready branch with vertex ai and docker containerization and solely Gemini/Claude pro 3.0 as the llm agent through vertex ai and connects directly to BigQuery"...

**This doesn't perfectly match any single branch:**

- **Closest match:** `integrate-claude-agents` has dual AI but no Docker
- **Second closest:** `docker` has Docker + Claude but not Gemini in app
- **Hybrid needed:** Combine `docker` (containerization) + `integrate-claude-agents` (dual AI)

**Vertex AI note:** All branches have `vertex_ai_analysis.py` script, but it's not heavily used. The main AI is:
- **Gemini API** (via google-genai SDK) - used in scripts
- **Claude API** (via anthropic SDK) - used in docker/integrate-claude-agents

---

## Recommendation

Based on what you described wanting, you probably want to merge:
- **Docker containerization** from `docker` branch
- **Dual AI capabilities** from `integrate-claude-agents` branch
- **Keep the production pipeline** from `main`

This would give you: Docker + Claude in app + Gemini in app + BigQuery + Vertex AI integration.

Is that accurate to what you're looking for?
