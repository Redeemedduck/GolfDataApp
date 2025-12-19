#!/usr/bin/env python3
"""
Analyze golf shot data using Claude AI with prompt caching for efficiency

This script provides an alternative to gemini_analysis.py, leveraging Claude's
strengths in conversational analysis, nuanced interpretation, and structured output.

Features:
- Prompt caching for cost efficiency (90% reduction on repeated analyses)
- Structured markdown output with emojis for readability
- Model flexibility (Opus for deep analysis, Sonnet for daily use, Haiku for automation)
- Drop-in replacement for gemini_analysis.py CLI interface

Usage:
    python claude_analysis.py                 # Analyze all clubs
    python claude_analysis.py Driver          # Analyze specific club
    python claude_analysis.py --model=opus    # Use Claude Opus for deep analysis
    python claude_analysis.py --interactive   # Start chat session
"""
import os
import sys
import anthropic
from google.cloud import bigquery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "valued-odyssey-474423-g1")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "golf_data")
BQ_TABLE_ID = os.getenv("BQ_TABLE_ID", "shots")

# Model configurations
MODELS = {
    "opus": "claude-opus-4",           # Best reasoning, deep analysis
    "sonnet": "claude-sonnet-4.5",     # Balanced performance/cost
    "haiku": "claude-haiku-4"          # Fast, cheap, good for automation
}

def get_bigquery_client():
    """Initialize BigQuery client"""
    return bigquery.Client(project=GCP_PROJECT_ID)

def query_shot_data(club=None, limit=500):
    """
    Query shot data from BigQuery with optional club filter

    Args:
        club: Filter by club name (e.g., 'Driver', '7 Iron')
        limit: Maximum number of rows to return

    Returns:
        pandas.DataFrame with shot data
    """
    bq_client = get_bigquery_client()
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

    query = f"""
        SELECT
            club,
            carry,
            total,
            side_distance,
            ball_speed,
            club_speed,
            smash,
            back_spin,
            side_spin,
            launch_angle,
            side_angle,
            attack_angle,
            club_path,
            face_angle,
            dynamic_loft,
            apex,
            flight_time,
            descent_angle,
            impact_x,
            impact_y,
            shot_type,
            date_added
        FROM `{table_id}`
    """

    # Use parameterized queries to prevent SQL injection
    job_config = bigquery.QueryJobConfig()
    query_parameters = []

    if club:
        query += " WHERE LOWER(club) LIKE LOWER(@club_filter)"
        query_parameters.append(
            bigquery.ScalarQueryParameter("club_filter", "STRING", f"%{club}%")
        )

    query += f" ORDER BY date_added DESC LIMIT {limit}"

    if query_parameters:
        job_config.query_parameters = query_parameters

    print(f"Fetching data from BigQuery...")
    df = bq_client.query(query, job_config=job_config).to_dataframe()
    print(f"Retrieved {len(df)} shots")

    return df

def build_system_context():
    """
    Build the system context for Claude with golf expertise and benchmarks

    Uses prompt caching to cache this expensive context, reducing costs by ~90%
    on repeated analyses within a 5-minute window.
    """
    return [
        {
            "type": "text",
            "text": """You are an expert golf performance analyst specializing in launch monitor data interpretation and swing coaching.

**YOUR EXPERTISE:**
- 20+ years analyzing PGA Tour player data
- Deep understanding of TrackMan, Uneekor, and launch monitor metrics
- Specialized knowledge of high-altitude golf (Denver: 5,280 ft elevation)
- Evidence-based coaching using biomechanics and data correlation

**PGA TOUR AVERAGES (ADJUSTED FOR DENVER ALTITUDE +5000ft):**

Driver:
- Ball Speed: 167 mph (sea level: 167 mph - minimal altitude effect)
- Club Speed: 112 mph (sea level: 112 mph)
- Smash Factor: 1.49 (optimal: 1.48-1.50)
- Launch Angle: 10.9° (optimal: 9-14° depending on spin)
- Back Spin: 2,686 rpm (Denver: ~2,400 rpm due to air density)
- Attack Angle: +1.3° (ascending blow)
- Carry Distance: 275 yards (Denver: +10-15 yards vs sea level)
- Total Distance: 296 yards (less roll due to altitude)

7 Iron:
- Ball Speed: 120 mph
- Club Speed: 87 mph
- Smash Factor: 1.38 (optimal: 1.36-1.40)
- Launch Angle: 16.3°
- Back Spin: 7,097 rpm (Denver: ~6,500 rpm)
- Attack Angle: -4.1° (descending blow)
- Carry Distance: 172 yards (Denver: +8-10 yards)
- Total Distance: 183 yards

**ANALYSIS FRAMEWORK:**

1. **Distance Efficiency:**
   - Smash factor optimization (ball speed / club speed)
   - Energy transfer quality
   - Center-face contact consistency
   - Ball speed ceiling vs current performance

2. **Consistency Analysis:**
   - Standard deviation of carry distance (Tour avg: 5-8 yards)
   - Standard deviation of side distance (Tour avg: 10-15 yards)
   - Coefficient of variation for key metrics
   - Outlier detection and frequency

3. **Shot Shape Control:**
   - Spin axis and shot curvature relationship
   - Face-to-path differential (face angle - club path)
   - Side spin patterns (positive = slice, negative = hook)
   - Launch direction vs intended target line

4. **Launch Optimization:**
   - Launch angle vs spin rate for max carry (higher/lower flight trade-off)
   - Peak height (apex) appropriateness for club type
   - Descent angle for stopping power
   - Altitude-adjusted optimal windows

5. **Swing Mechanics Patterns:**
   - Attack angle consistency and appropriateness
   - Club path tendencies (in-to-out vs out-to-in)
   - Face angle at impact (open/closed patterns)
   - Dynamic loft vs static loft
   - Impact location dispersion (toe/heel, high/low)

**OUTPUT STRUCTURE:**
Provide analysis in this exact markdown format:

# 🏌️ Golf Performance Analysis: [Club Name]

## 📊 Data Summary
- Total Shots: X
- Date Range: [earliest] to [latest]
- Session Count: Y

## 🎯 Key Strengths (2-3 bullets)
- [Specific metric with comparison to Tour average]
- [Pattern showing positive performance]
- [Consistency highlight if applicable]

## ⚠️ Primary Areas for Improvement (2-3 bullets)
- [Specific metric with gap to Tour average]
- [Pattern showing limiting factor]
- [Consistency concern with standard deviation]

## 📈 Consistency Analysis
| Metric | Your Avg | Std Dev | Tour Avg | Assessment |
|--------|----------|---------|----------|------------|
| Carry  | X yds    | Y yds   | Z yds    | [Good/Fair/Needs Work] |
| [2-3 more key metrics]

## 🔍 Detailed Insights

### Distance Efficiency
[Analysis paragraph with specific numbers]

### Shot Shape Control
[Analysis paragraph with face/path relationship]

### Launch Conditions
[Analysis paragraph with altitude context]

## 💡 Actionable Recommendations

### Priority #1: [Specific Focus Area]
- **Drill:** [Specific practice drill with setup]
- **Feel:** [What to feel during execution]
- **Measurement:** [How to know if improving]

### Priority #2: [Secondary Focus]
- **Drill:** [Specific practice drill]
- **Feel:** [Feel description]
- **Measurement:** [Success metric]

### Priority #3: [Tertiary Focus]
- **Drill:** [Specific practice drill]
- **Feel:** [Feel description]
- **Measurement:** [Success metric]

## 🎓 Key Takeaway
[One inspiring sentence summarizing the main insight and path forward]

---

**IMPORTANT GUIDELINES:**
- Always provide specific numbers, not vague assessments
- Compare to altitude-adjusted Tour averages, not sea level
- Identify correlations between metrics (e.g., "when club path is X, side spin is Y")
- Prioritize actionable insights over generic advice
- Be encouraging but honest about gaps
- Focus on 1-2 key improvements, not overwhelming lists
- Explain WHY a metric matters, not just WHAT it is
""",
            "cache_control": {"type": "ephemeral"}  # Cache this ~2000 token context
        }
    ]

def analyze_with_claude(club=None, model="sonnet", show_usage=True):
    """
    Send shot data to Claude for expert analysis

    Args:
        club: Specific club to analyze (None = all clubs)
        model: Model to use ("opus", "sonnet", or "haiku")
        show_usage: Display token usage statistics

    Returns:
        str: Analysis text from Claude
    """
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        return None

    # Fetch data
    df = query_shot_data(club=club)

    if df.empty:
        print(f"No data found{f' for club: {club}' if club else ''}")
        return None

    # Prepare data context
    csv_data = df.to_csv(index=False)

    # Calculate quick statistics for context
    total_shots = len(df)
    clubs_analyzed = df['club'].unique().tolist()
    date_range = f"{df['date_added'].min()} to {df['date_added'].max()}"

    # Build user message
    user_message = f"""Please analyze this golf shot data:

**Context:**
- Total Shots: {total_shots}
- Clubs: {', '.join(clubs_analyzed)}
- Date Range: {date_range}
- Location: Denver, CO (5,280 ft elevation)

**Raw Data (CSV format):**
```csv
{csv_data}
```

**Analysis Request:**
Provide a comprehensive performance analysis using your framework. Focus on:
1. What I'm doing well (with specific metrics)
2. My biggest limiting factors (with gap analysis)
3. Consistency patterns (dispersion statistics)
4. Specific, actionable drills to improve

Remember: This data is from Denver altitude - adjust Tour comparisons accordingly.
"""

    # Initialize Claude client
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print(f"\n{'='*70}")
    print(f"Analyzing with Claude {model.upper()}...")
    print(f"{'='*70}\n")

    try:
        response = client.messages.create(
            model=MODELS[model],
            max_tokens=4096,
            system=build_system_context(),
            messages=[{"role": "user", "content": user_message}]
        )

        # Extract text
        analysis_text = response.content[0].text

        # Display analysis
        print(analysis_text)

        # Show usage statistics
        if show_usage:
            usage = response.usage
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0)
            cache_read = getattr(usage, 'cache_read_input_tokens', 0)

            print(f"\n{'='*70}")
            print("TOKEN USAGE STATISTICS")
            print(f"{'='*70}")
            print(f"Input Tokens: {input_tokens:,}")
            print(f"Output Tokens: {output_tokens:,}")
            if cache_creation > 0:
                print(f"Cache Creation: {cache_creation:,} (first run - builds cache)")
            if cache_read > 0:
                print(f"Cache Read: {cache_read:,} (90% cost savings!)")

            # Estimate cost
            costs = {
                "opus": {"input": 15, "output": 75, "cache_write": 18.75, "cache_read": 1.5},
                "sonnet": {"input": 3, "output": 15, "cache_write": 3.75, "cache_read": 0.3},
                "haiku": {"input": 0.25, "output": 1.25, "cache_write": 0.3, "cache_read": 0.03}
            }

            cost_config = costs[model]
            input_cost = (input_tokens / 1_000_000) * cost_config["input"]
            output_cost = (output_tokens / 1_000_000) * cost_config["output"]
            cache_creation_cost = (cache_creation / 1_000_000) * cost_config["cache_write"]
            cache_read_cost = (cache_read / 1_000_000) * cost_config["cache_read"]

            total_cost = input_cost + output_cost + cache_creation_cost + cache_read_cost

            print(f"\nEstimated Cost: ${total_cost:.4f}")
            if cache_read > 0:
                non_cached_cost = ((input_tokens + cache_read) / 1_000_000) * cost_config["input"] + output_cost
                savings = non_cached_cost - total_cost
                print(f"Cache Savings: ${savings:.4f} ({(savings/non_cached_cost)*100:.1f}%)")
            print(f"{'='*70}\n")

        return analysis_text

    except anthropic.APIError as e:
        print(f"Claude API Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def interactive_chat_mode(club=None, model="sonnet"):
    """
    Start an interactive chat session with Claude about golf data

    Args:
        club: Optional club filter for data context
        model: Model to use for chat
    """
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not found")
        return

    # Fetch initial data
    df = query_shot_data(club=club)
    if df.empty:
        print("No data available for chat")
        return

    csv_data = df.to_csv(index=False)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    conversation_history = []

    print(f"\n{'='*70}")
    print(f"CLAUDE GOLF COACH - Interactive Chat Mode")
    print(f"Model: {MODELS[model]}")
    print(f"Data loaded: {len(df)} shots{f' ({club})' if club else ''}")
    print(f"{'='*70}")
    print("\nType your questions about your golf data. Type 'quit' to exit.\n")

    # Initial system message with data
    initial_context = f"""You are chatting with a golfer about their shot data.

Data context (CSV):
```csv
{csv_data}
```

Be conversational, encouraging, and specific. Reference their actual numbers.
Ask clarifying questions when needed. Suggest drills and improvements."""

    while True:
        user_input = input("\n🏌️ You: ").strip()

        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Thanks for the session! Keep practicing!\n")
            break

        if not user_input:
            continue

        # Add to conversation
        conversation_history.append({"role": "user", "content": user_input})

        try:
            # For first message, include data context
            messages = conversation_history.copy()
            if len(conversation_history) == 1:
                messages[0]["content"] = f"{initial_context}\n\nQuestion: {user_input}"

            response = client.messages.create(
                model=MODELS[model],
                max_tokens=2048,
                system=build_system_context(),
                messages=messages
            )

            assistant_message = response.content[0].text
            conversation_history.append({"role": "assistant", "content": assistant_message})

            print(f"\n🤖 Claude: {assistant_message}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            # Remove failed user message
            conversation_history.pop()

def print_usage():
    """Print CLI usage instructions"""
    print("""
Claude Golf Analysis - Usage Guide

BASIC USAGE:
    python claude_analysis.py                    # Analyze all clubs
    python claude_analysis.py Driver             # Analyze specific club
    python claude_analysis.py "7 Iron"           # Use quotes for clubs with spaces

MODEL SELECTION:
    python claude_analysis.py --model=opus       # Deep analysis (best quality)
    python claude_analysis.py --model=sonnet     # Balanced (default)
    python claude_analysis.py --model=haiku      # Fast summary (cheapest)

    python claude_analysis.py Driver --model=opus  # Combine club + model

INTERACTIVE MODE:
    python claude_analysis.py --interactive      # Chat about all data
    python claude_analysis.py Driver --interactive  # Chat about specific club

EXAMPLES:
    # Daily quick check with Haiku
    python claude_analysis.py --model=haiku

    # Deep driver analysis with Opus
    python claude_analysis.py Driver --model=opus

    # Interactive coaching session
    python claude_analysis.py --interactive

    # Compare to Gemini (run both)
    python claude_analysis.py Driver && python gemini_analysis.py Driver

COST ESTIMATES (per analysis):
    Haiku:  ~$0.004  (great for daily automation)
    Sonnet: ~$0.05   (best for regular use)
    Opus:   ~$0.25   (save for weekly deep dives)

    Prompt caching reduces costs by ~90% on repeated runs!

NOTES:
    - First run creates cache (slightly more expensive)
    - Subsequent runs within 5 minutes use cache (much cheaper)
    - Interactive mode maintains conversation context
    - All analyses use Denver altitude-adjusted benchmarks
""")

def main():
    """Main CLI entry point"""
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print_usage()
        return 0

    # Parse arguments
    club = None
    model = "sonnet"
    interactive = False

    for arg in args:
        if arg.startswith("--model="):
            model = arg.split("=")[1].lower()
            if model not in MODELS:
                print(f"Error: Invalid model '{model}'. Choose from: opus, sonnet, haiku")
                return 1
        elif arg == "--interactive" or arg == "-i":
            interactive = True
        elif not arg.startswith("--"):
            club = arg

    # Execute
    if interactive:
        interactive_chat_mode(club=club, model=model)
    else:
        analyze_with_claude(club=club, model=model, show_usage=True)

    return 0

if __name__ == "__main__":
    sys.exit(main())
