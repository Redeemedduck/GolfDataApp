# Unified Branch Integration Plan

**Branch:** `claude/unified-ai-docker-integration`
**Base:** `main` (production-ready with Gemini 3 Pro + MCP)
**Date:** 2025-12-24

## 🎯 Objective

Create a unified branch combining:
1. **Main branch**: Gemini 3 Pro + BigQuery + MCP Control Plane
2. **Docker branch**: Full containerization + Claude AI in Streamlit
3. **New features**: Both Claude AND Gemini in Streamlit app

---

## ✅ Already Completed

### 1. Branch Created
- Created `claude/unified-ai-docker-integration` from `main`
- Preserves all production features from main

### 2. Docker Files Merged
- ✅ Dockerfile (multi-stage, optimized)
- ✅ docker-compose.yml
- ✅ .dockerignore
- ✅ DOCKER_GUIDE.md (comprehensive documentation)
- ✅ DOCKER_README.md
- ✅ DOCKER_SETUP_COMPLETE.md
- ✅ docker-quickstart.sh
- ✅ .env.docker.example

---

## 📋 Still TODO

### 1. Enhance app.py with Dual AI
**Goal:** Add both Claude AND Gemini to Streamlit app

**Features to add:**
```python
# AI availability detection
ANTHROPIC_AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))
GEMINI_AVAILABLE = bool(os.getenv("GEMINI_API_KEY"))

# Model selector in AI Coach tab
models = [
    "Claude Sonnet",      # Conversational
    "Claude Opus",        # Best quality
    "Claude Haiku",       # Fastest
    "Gemini 3 Pro (Code)", # Code execution
    "Gemini Flash"         # Quick insights
]
```

**Reference Implementation:**
- See `claude/fix-supabase-gemini-issues-PXRya` branch app.py (lines 1-538)
- Has complete dual AI integration
- Includes session-aware context
- Robust error handling

### 2. Fix Supabase RLS Security
**Current Issue:** RLS policies only allow `authenticated` users, but app uses `anon` key

**Solution:** Add policies for `anon` role in `supabase_schema.sql`:

```sql
-- Add after line 67
CREATE POLICY "Allow anon to read shots"
ON shots FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow anon to insert shots"
ON shots FOR INSERT
TO anon
WITH CHECK (true);

CREATE POLICY "Allow anon to update shots"
ON shots FOR UPDATE
TO anon
USING (true);

CREATE POLICY "Allow anon to delete shots"
ON shots FOR DELETE
TO anon
USING (true);
```

### 3. Update Documentation

**CLAUDE.md updates needed:**
- Document dual AI integration in Streamlit
- Update architecture diagram
- Add Docker containerization section
- Document model selection feature

**New section to add:**
```markdown
### AI Coach (In-App)

The Streamlit app now includes an AI Coach tab with multiple models:

**Claude (Anthropic):**
- Sonnet: Balanced performance
- Opus: Best quality analysis
- Haiku: Fastest responses

**Gemini (Google):**
- 3 Pro (Code): Runs Python analysis on your data
- Flash: Quick conversational insights

**Setup:**
```bash
# Add to .env
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```
```

### 4. Test Docker Build
```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Test AI features
# - Import data
# - Try Claude models
# - Try Gemini models
# - Verify code execution works
```

---

## 🏗️ Architecture Overview

### Current (Main Branch)
```
Uneekor API → SQLite (local) → Supabase (backup) → BigQuery (analytics)
                                                         ↓
                                                   Gemini 3 Pro (scripts)
                                                         ↓
                                                 MCP Control Plane
```

### Target (Unified Branch)
```
                  ┌─ Docker Container ────────────────────────┐
                  │                                            │
Uneekor API ──────┼→ Streamlit App (app.py)                   │
                  │    ├─ Dashboard                           │
                  │    ├─ Shot Viewer                         │
                  │    ├─ Data Management                     │
                  │    └─ 🤖 AI Coach (NEW!)                  │
                  │         ├─ Claude Sonnet/Opus/Haiku       │
                  │         └─ Gemini 3 Pro / Flash           │
                  │          ↓                                 │
                  │    SQLite (local-first)                   │
                  │          ↓                                 │
                  └──────────┼─────────────────────────────────┘
                             ↓
                      Supabase (cloud backup)
                             ↓
                      BigQuery (analytics)
                             ↓
                      MCP Control Plane
```

**Key Differences:**
1. ✨ **AI in App**: Both Claude and Gemini accessible from Streamlit
2. 🐳 **Docker**: Fully containerized with OrbStack optimization
3. 🔄 **Same Data Flow**: Preserves existing Supabase + BigQuery pipeline
4. 🔒 **Fixed RLS**: Secure anon policies

---

## 📦 Dependencies

### Current (main branch)
```
streamlit
pandas
plotly
requests
supabase
python-dotenv
google-generativeai
```

### Needed Additions
```
anthropic          # For Claude AI
```

---

## 🚀 Implementation Steps

### Step 1: Update app.py (30 min)
1. Add AI detection (lines 10-28)
2. Add client initialization functions (lines 32-54)
3. Add session_summary generator (lines 56-82)
4. Add AI Coach tab (lines 318-537)
5. Test locally: `streamlit run app.py`

### Step 2: Fix Supabase RLS (5 min)
1. Update `supabase_schema.sql`
2. Run in Supabase SQL Editor
3. Verify with test insert

### Step 3: Update requirements.txt (1 min)
```bash
echo "anthropic" >> requirements.txt
```

### Step 4: Test Docker (10 min)
```bash
docker-compose build
docker-compose up -d
open http://localhost:8501
```

### Step 5: Update Documentation (15 min)
1. Update CLAUDE.md
2. Add AI Coach section
3. Update architecture diagrams
4. Document new features

### Step 6: Commit and Push (5 min)
```bash
git add -A
git commit -m "feat: unified branch with Docker + dual AI + RLS fixes"
git push -u origin claude/unified-ai-docker-integration
```

---

## 🎁 Benefits of Unified Branch

| Feature | Main | Docker | Unified |
|---------|------|--------|---------|
| Gemini 3 Pro | ✅ Scripts | ❌ | ✅ In-app |
| Claude AI | ❌ | ✅ In-app | ✅ In-app |
| Docker | ❌ | ✅ | ✅ |
| BigQuery | ✅ | ✅ | ✅ |
| MCP | ✅ | ❌ | ✅ |
| Supabase RLS | ⚠️ Broken | ⚠️ Broken | ✅ Fixed |
| Code Execution | ✅ Scripts | ❌ | ✅ In-app |

**Result:** Best of all worlds! 🎉

---

## 📝 Notes

- **Main branch** is production-ready base
- **Docker branch** has containerization + Claude
- **Feature branch** (claude/fix-supabase-gemini-issues-PXRya) has dual AI implementation
- **This branch** will combine all three

---

## 🤔 Questions for User

1. **Keep Supabase?** Or switch to SQLite → BigQuery only?
2. **Model preferences?** Should we default to Claude or Gemini?
3. **Docker resources?** Any specific CPU/memory limits needed?
4. **Deployment target?** Local only or cloud deployment planned?

---

## 📞 Next Actions

**For User:**
1. Review this plan
2. Confirm architecture approach
3. Test Docker setup locally
4. Provide feedback on AI model selection

**For Implementation:**
1. Copy AI Coach code from feature branch
2. Fix Supabase RLS
3. Test end-to-end
4. Update all documentation
5. Create PR to main

---

## 🔗 Related Files

- Main implementation: `app.py`
- Database: `golf_db.py` (already has Supabase hybrid)
- AI scripts: `scripts/gemini_analysis.py`, `scripts/claude_analysis.py`
- Docker: All `DOCKER_*.md` files
- Schema: `supabase_schema.sql`

---

**Status:** Docker files merged ✅
**Next:** Implement dual AI in app.py
**ETA:** 1 hour of focused work
