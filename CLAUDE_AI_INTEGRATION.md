# Claude AI Integration Guide

## Overview

This golf data analysis platform now features **multi-agent AI analysis** using both Claude and Gemini AI for comprehensive golf swing insights. Each AI brings unique strengths to golf coaching and data interpretation.

## New Features Added

### 1. Claude Analysis Script (`scripts/claude_analysis.py`)

Standalone AI analysis tool powered by Claude with prompt caching for cost efficiency.

**Usage:**
```bash
# Analyze all clubs
python scripts/claude_analysis.py

# Analyze specific club
python scripts/claude_analysis.py Driver

# Choose model (opus = best, sonnet = balanced, haiku = fast)
python scripts/claude_analysis.py --model=opus
python scripts/claude_analysis.py Driver --model=sonnet

# Interactive chat mode
python scripts/claude_analysis.py --interactive
python scripts/claude_analysis.py Driver --interactive
```

**Key Features:**
- Prompt caching (90% cost reduction on repeated analyses)
- Structured markdown output with coaching recommendations
- Model flexibility (Opus/Sonnet/Haiku)
- Interactive chat mode for Q&A
- Altitude-adjusted PGA Tour benchmarks

**Cost per Analysis:**
- Haiku: ~$0.004 (great for automation)
- Sonnet: ~$0.05 (balanced daily use)
- Opus: ~$0.25 (weekly deep dives)

---

### 2. Multi-Agent Comparison Tool (`scripts/compare_ai_analysis.py`)

Run both Claude and Gemini on the same data to get complementary insights.

**Usage:**
```bash
# Basic comparison
python scripts/compare_ai_analysis.py
python scripts/compare_ai_analysis.py Driver

# Save results to file
python scripts/compare_ai_analysis.py --save

# Use Claude Opus for deeper analysis
python scripts/compare_ai_analysis.py Driver --claude-model=opus --save
```

**Why Compare?**
- **Claude Strengths**: Conversational coaching, nuanced interpretation, drill recommendations
- **Gemini Strengths**: Code execution for statistics, mathematical correlations, pattern detection
- **Agreement = Priority**: When both identify the same issue, it's a high-confidence recommendation
- **Disagreement = Insight**: Different perspectives reveal nuanced patterns

**Output:**
- Side-by-side analysis from both AIs
- Performance comparison (time, success rate)
- Saved markdown reports in `analysis_reports/`
- Actionable summary combining both perspectives

---

### 3. Interactive AI Coach (Streamlit App)

New "AI Coach" tab in the Streamlit app for conversational golf analysis.

**Features:**
- Real-time chat with Claude about your swing data
- Model selector (Opus/Sonnet/Haiku)
- Persistent conversation history
- Quick analysis button
- Session data automatically included as context
- Example questions provided

**How to Use:**
1. Launch app: `streamlit run app.py`
2. Select a session
3. Click "AI Coach" tab
4. Ask questions about your data:
   - "Why am I pulling my driver left?"
   - "How can I improve consistency?"
   - "What drill should I work on?"
   - "Compare my stats to tour average"

**Model Selection:**
- **Sonnet (Balanced)**: Best for most conversational coaching (default)
- **Opus (Best)**: Deep swing analysis and complex questions
- **Haiku (Fast)**: Quick answers and simple clarifications

**Controls:**
- Clear Chat History: Reset conversation
- Quick Analysis: Get instant top 3 focus areas

---

## Setup Instructions

### Prerequisites

1. **Anthropic API Key**

Obtain from: https://console.anthropic.com/

Add to `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-api...
```

2. **Python Dependencies**

Already installed if you have `requirements.txt`:
```bash
anthropic>=0.39.0
```

Verify installation:
```bash
python -c "import anthropic; print('Claude SDK installed!')"
```

### First-Time Setup

1. Set API key in `.env`:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-api..." >> .env
```

2. Test Claude connection:
```bash
python scripts/claude_analysis.py --help
```

3. Run first analysis:
```bash
python scripts/claude_analysis.py Driver --model=haiku
```

4. (Optional) Compare with Gemini:
```bash
python scripts/compare_ai_analysis.py Driver
```

---

## Integration Architecture

### Data Flow

```
BigQuery (Data Warehouse)
    ↓
claude_analysis.py (Query + Analyze)
    ↓
Claude API (Opus/Sonnet/Haiku)
    ↓
Structured Coaching Insights
```

### Prompt Caching Strategy

Claude's prompt caching stores expensive system instructions (PGA benchmarks, coaching framework) for 5 minutes:

- **First request**: Builds cache (~2000 tokens cached)
- **Subsequent requests**: Reads from cache (90% cost savings)
- **Cache lifetime**: 5 minutes from last access

**Example Cost Savings:**
- Without caching: ~$0.06 per analysis (Sonnet)
- With caching: ~$0.006 per analysis (10x cheaper!)

### System Prompt Components

1. **Golf Expertise**: 20+ years experience, launch monitor specialization
2. **PGA Tour Benchmarks**: Altitude-adjusted for Denver (5,280 ft)
3. **Analysis Framework**: 5-step coaching methodology
4. **Output Structure**: Markdown template with emojis

---

## AI Model Comparison

### When to Use Claude

**Best For:**
- Conversational coaching and Q&A
- Nuanced swing interpretation
- Drill and practice recommendations
- Contextual explanations
- Multi-turn coaching dialogues

**Strengths:**
- Superior instruction following
- Better coaching tone and encouragement
- Excellent at structured output
- Strong at contextual reasoning

**Use Cases:**
- Interactive coaching sessions
- Personalized practice plans
- Explaining "why" behind metrics
- Motivational feedback

---

### When to Use Gemini

**Best For:**
- Statistical analysis and calculations
- Mathematical correlations
- Pattern detection in large datasets
- Code-driven insights

**Strengths:**
- Python code execution for analysis
- Advanced statistical computations
- Data visualization generation
- Numerical precision

**Use Cases:**
- Dispersion analysis
- Correlation studies
- Trend identification
- Performance tracking

---

### Multi-Agent Strategy

**Recommended Workflow:**

1. **Weekly Deep Dive (Both AIs)**:
   ```bash
   python scripts/compare_ai_analysis.py --save
   ```
   - Get comprehensive perspective
   - Identify high-priority improvements
   - Set weekly goals

2. **Daily Quick Check (Claude Haiku)**:
   ```bash
   python scripts/claude_analysis.py --model=haiku
   ```
   - Fast feedback on practice session
   - Track improvement on focus areas
   - Stay motivated

3. **Interactive Sessions (Claude Sonnet)**:
   ```bash
   streamlit run app.py
   ```
   - Ask follow-up questions
   - Clarify confusing metrics
   - Get drill modifications

4. **Statistical Deep Dive (Gemini)**:
   ```bash
   python scripts/gemini_analysis.py Driver
   ```
   - Detailed mathematical analysis
   - Correlation discoveries
   - Precision measurements

---

## Cost Management

### Monthly Budget Estimates

**Light Usage** (10 analyses/month):
- Claude Haiku: $0.04
- Claude Sonnet: $0.50
- Gemini: $1.00
- **Total: ~$1.50/month**

**Regular Usage** (30 analyses/month):
- Claude Haiku (daily): $0.12
- Claude Sonnet (weekly): $0.35
- Claude Opus (weekly): $1.00
- Gemini (weekly): $0.40
- **Total: ~$2/month**

**Power User** (100+ analyses/month):
- Mix of all models: ~$10-15/month

### Cost Optimization Tips

1. **Use Haiku for Automation**: Set up daily auto-analysis with Haiku
2. **Enable Prompt Caching**: Rerun within 5 minutes for 90% savings
3. **Save Opus for Deep Dives**: Weekly comprehensive reviews only
4. **Batch Questions**: Ask multiple questions in one chat session
5. **Use Comparison Sparingly**: Run weekly, not daily

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
```bash
# Check .env file exists
ls -la .env

# Verify key is set
grep ANTHROPIC_API_KEY .env

# Load manually
export ANTHROPIC_API_KEY=sk-ant-api...
```

### "anthropic package not installed"
```bash
pip install anthropic
# or
pip install -r requirements.txt
```

### Claude API Error
- Check API key is valid at console.anthropic.com
- Verify account has credits
- Check internet connection
- Review rate limits (tier-based)

### Streamlit AI Coach Tab Missing
- Verify ANTHROPIC_API_KEY is set in .env
- Restart Streamlit app
- Check terminal for import errors

---

## Advanced Usage

### Custom Analysis Prompts

Modify `claude_analysis.py` system prompt for specialized analysis:

```python
# Add custom coaching focus
system_prompt += """
ADDITIONAL FOCUS: Analyze for senior golfer (slower swing speed, prioritize consistency over distance)
"""
```

### Integration with Automation

Add Claude analysis to daily automation:

```bash
# In auto_sync.py or post_session.py
from claude_analysis import analyze_with_claude

# After data sync
analyze_with_claude(club="Driver", model="haiku")
```

### Export Analysis History

Save all AI insights for long-term tracking:

```bash
# Use comparison tool with --save flag
python scripts/compare_ai_analysis.py --save

# Results stored in analysis_reports/
ls -lt analysis_reports/
```

---

## Future Enhancements

### Planned Features

1. **Image Analysis**: Claude vision API for impact/swing images
2. **Voice Coaching**: Audio responses for hands-free feedback
3. **Video Integration**: Swing video analysis with Claude vision
4. **Training Plans**: Multi-week personalized programs
5. **Progress Tracking**: Automated improvement measurement
6. **Tournament Prep**: Pre-round strategy and course management

### Community Contributions

See `CLAUDE_INTEGRATION_RECOMMENDATIONS.md` for comprehensive enhancement ideas.

---

## Quick Reference

### Common Commands

```bash
# Analysis
python scripts/claude_analysis.py                    # Analyze all
python scripts/claude_analysis.py Driver            # Specific club
python scripts/claude_analysis.py --model=opus      # Best quality

# Comparison
python scripts/compare_ai_analysis.py Driver --save  # Save results

# Interactive
python scripts/claude_analysis.py --interactive      # CLI chat
streamlit run app.py                                 # UI chat (AI Coach tab)
```

### File Locations

- Scripts: `scripts/claude_analysis.py`, `scripts/compare_ai_analysis.py`
- App integration: `app.py` (AI Coach tab)
- Documentation: `CLAUDE_AI_INTEGRATION.md` (this file)
- Recommendations: `CLAUDE_INTEGRATION_RECOMMENDATIONS.md`
- Analysis reports: `analysis_reports/` (created automatically)

---

## Support

**Questions or Issues?**
1. Check this documentation
2. Review `CLAUDE_INTEGRATION_RECOMMENDATIONS.md` for detailed examples
3. Check Anthropic API status: https://status.anthropic.com
4. Review Claude API docs: https://docs.anthropic.com

**Feedback Welcome!**
- Feature requests
- Bug reports
- Integration ideas
- Coaching prompt improvements

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Compatible With**: Claude Opus 4, Claude Sonnet 4.5, Claude Haiku 4
