# Vertex AI Conversational Golf Coach - User Guide

## Overview

The Vertex AI Golf Coach Agent is a conversational AI that provides:
- **Multi-turn conversation memory** - Remembers your entire coaching session
- **Direct BigQuery access** - Queries your 555 historical shots via function calling
- **Automated analysis** - Calculates statistics, finds patterns, identifies trends
- **Personalized recommendations** - Compares your performance to PGA Tour averages (altitude-adjusted)
- **Proactive insights** - Can analyze your game without you even asking

## Setup Complete ✅

All Phase 1 tasks are complete:
- ✅ Vertex AI APIs enabled (aiplatform, discoveryengine, dialogflow)
- ✅ BigQuery data store connected (valued-odyssey-474423-g1.golf_data.shots)
- ✅ Custom golf analysis tools defined (5 tools for querying, stats, comparison, patterns, summaries)
- ✅ Conversational agent built with memory
- ✅ Tested and working with 555 shots

## Usage

### Python API (Programmatic Access)

```python
from vertex_ai_agent import create_golf_coach

# Create agent
coach = create_golf_coach()

# Single question
response = coach.chat("What's my average carry distance with the Driver?")
print(response)

# Follow-up question (agent remembers context)
response = coach.chat("How does that compare to PGA Tour averages?")
print(response)

# Another follow-up
response = coach.chat("What should I focus on improving?")
print(response)

# Get proactive insights
insights = coach.get_proactive_insights()
print(insights)

# Start a new conversation
response = coach.chat("Analyze my 7 Iron performance", reset_history=True)
print(response)
```

### Command Line (Interactive Testing)

```bash
# Run the example conversation
python vertex_ai_agent.py

# Output shows:
# - Average carry distance with Driver (275.9 yards)
# - PGA Tour comparison (adjusted for Denver altitude)
# - Personalized improvement recommendations
# - Total shots analyzed in session
```

### Integration Points

The agent can be used in multiple ways:

1. **Standalone Python Scripts**
   ```python
   # scripts/vertex_coach_analysis.py
   from vertex_ai_agent import create_golf_coach

   coach = create_golf_coach()
   print(coach.chat("Give me a comprehensive analysis of my Driver"))
   ```

2. **Jupyter Notebooks**
   ```python
   # notebooks/golf_analysis.ipynb
   import vertex_ai_agent

   coach = vertex_ai_agent.create_golf_coach()

   # Cell 1: Get Driver stats
   coach.chat("Show me Driver statistics")

   # Cell 2: Compare clubs
   coach.chat("How does my 7 Iron compare to my 8 Iron?")
   ```

3. **Streamlit App** (Future Integration)
   - Add as model option: "Conversational Agent (Vertex AI)"
   - Provides multi-turn memory vs current stateless Gemini implementation
   - Automatic BigQuery tool calling vs manual CSV passing

4. **REST API** (Future Integration)
   - Wrap agent in FastAPI endpoint
   - Deploy to Cloud Run
   - Access from any device via HTTP

## Agent Capabilities

### Tool 1: Query Golf Shots
```python
# The agent can query BigQuery directly
coach.chat("Show me my last 10 Driver shots")
coach.chat("What were my best 5 shots with the 7 Iron?")
coach.chat("Show me all shots from session 12345")
```

### Tool 2: Get Club Statistics
```python
# Comprehensive statistics for any club
coach.chat("What are my Driver statistics?")
coach.chat("Show me detailed stats for my Pitching Wedge")

# Returns: shot count, averages, standard deviations, min/max for:
# - carry, ball speed, club speed, smash factor
# - launch angle, spin rates, club path, face angle
# - attack angle, dispersion
```

### Tool 3: Compare Clubs
```python
# Side-by-side club comparison
coach.chat("Compare my Driver, 3 Wood, and 5 Iron")
coach.chat("How do my irons compare to each other?")
```

### Tool 4: Analyze Shot Patterns
```python
# Pattern detection and correlation analysis
coach.chat("What patterns do you see in my Driver shots?")
coach.chat("Is there a correlation between club path and side spin?")
coach.chat("Analyze my slice/hook tendencies")

# Returns: correlations, shot type distribution, summary stats
```

### Tool 5: Get Session Summary
```python
# Comprehensive session analysis
coach.chat("Summarize my most recent practice session")
coach.chat("Give me a summary of session 84428")

# Returns: session duration, total shots, clubs used,
#         best shots, key metrics, areas for improvement
```

## Example Conversations

### Conversation 1: Driver Analysis
```
You: "What's my average carry distance with the Driver?"

Coach: "Your average carry distance with the Driver is 275.9 yards. Given that
you are playing in Denver, the altitude is likely helping you get a bit more
distance. I also see a standard deviation of 24.3 yards. This indicates some
inconsistency in your Driver distance. Let's see if we can tighten that up!"

You: "How does that compare to PGA Tour averages?"

Coach: "The PGA Tour average carry distance with the driver is about 270 yards
at sea level. Adjusted for Denver's altitude (roughly 10% more distance), this
would be around 297 yards. Your current average of 275.9 yards is about 21 yards
shorter than the PGA Tour average, adjusted for altitude. While not drastically
different, there's definitely room for improvement."

You: "What should I focus on improving?"

Coach: "Based on your data, here are key areas to focus on:

1. **Ball Speed**: Your average ball speed is 125.8 mph. PGA Tour players
   typically generate 165-185 mph. Increasing ball speed is crucial for
   maximizing distance. Work on swing efficiency and center-face contact.

2. **Smash Factor**: Your average is 1.40. Tour players are closer to 1.5.
   This suggests you're losing energy at impact.

3. **Launch Angle**: Your 16.7° launch might be slightly high. Consider
   optimizing it in relation to your spin rate.

Next session: Focus on making cleaner contact and increasing ball speed.
Consider a professional club fitting to optimize your launch conditions."
```

### Conversation 2: Session Review
```
You: "Summarize my last practice session"

Coach: "Here's your session summary:

**Session Details:**
- Start: 2024-12-15 14:30
- Duration: 1 hour 45 minutes
- Total Shots: 87
- Clubs Used: Driver, 7 Iron, Pitching Wedge, Sand Wedge

**Performance Highlights:**
- Best Carry: 289 yards (Driver, Shot #23)
- Best Smash: 1.48 (Driver, Shot #45)
- Most Consistent: Pitching Wedge (std dev: 8.2 yards)

**Areas for Improvement:**
- Driver dispersion (avg side distance: 15.3 yards)
- 7 Iron launch angle consistency (std dev: 3.4°)

**Recommendations:**
1. Work on Driver alignment and face control
2. Focus on 7 Iron tempo for more consistent launch
3. Your Pitching Wedge is dialed in - great work!"
```

### Conversation 3: Pattern Analysis
```
You: "Do you see any patterns in my ball flight?"

Coach: "Analyzing your shot patterns across all clubs, here's what I found:

**Correlation Analysis:**
- Strong positive correlation (0.78) between club path and side spin
  → When you swing in-to-out, you generate draw spin
- Negative correlation (-0.62) between face angle and side distance
  → Open face = shots to the right
- Moderate correlation (0.45) between attack angle and carry distance
  → More ascending blow = more distance

**Shot Shape Distribution:**
- Straight: 42%
- Hook/Draw: 31%
- Slice/Fade: 27%

**Key Insight:**
Your club path is generally good (in-to-out), but your face angle isn't always
matching it. When your face is square to slightly closed relative to path, you
hit great shots. When the face gets open, you lose shots to the right.

**Drill Recommendation:**
Practice face control drills. Try hitting shots with an intentional draw, then
a fade, to develop better feel for face position at impact."
```

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Vertex AI Golf Coach                      │
│                                                               │
│  ┌─────────────────────┐    ┌───────────────────────┐       │
│  │  Gemini 2.0 Flash   │◄──►│  Conversation Memory  │       │
│  │  (Model)            │    │  (Multi-turn Context)  │       │
│  └──────────┬──────────┘    └───────────────────────┘       │
│             │                                                 │
│             │ Function Calling                                │
│             ▼                                                 │
│  ┌──────────────────────────────────────────────┐            │
│  │              5 Golf Analysis Tools             │            │
│  ├────────────────────────────────────────────────┤            │
│  │  1. query_golf_shots()                        │            │
│  │  2. get_club_statistics()                     │            │
│  │  3. compare_clubs_performance()               │            │
│  │  4. analyze_shot_patterns()                   │            │
│  │  5. get_session_summary()                     │            │
│  └──────────────────┬───────────────────────────┘            │
│                     │                                         │
│                     ▼                                         │
│  ┌──────────────────────────────────────────────┐            │
│  │            BigQuery Client                     │            │
│  │  valued-odyssey-474423-g1.golf_data.shots     │            │
│  │                                               │            │
│  │  • 555 historical shots                       │            │
│  │  • 32 columns of metrics                      │            │
│  │  • Indexed for fast queries                   │            │
│  └────────────────────────────────────────────────┘            │
└───────────────────────────────────────────────────────────┘
```

## System Instruction (Coaching Philosophy)

The agent is instructed to:
- **Be conversational and encouraging**, but data-driven
- **Remember context** from earlier in the conversation
- **Compare to PGA Tour averages**, adjusted for Denver altitude (5,280 ft)
- **Identify patterns and correlations** in swing metrics
- **Provide specific, actionable recommendations**
- **Reference actual shot numbers** when discussing performance
- **Track improvement over time** across multiple sessions

## Performance Characteristics

- **Response Time**: 2-5 seconds (includes BigQuery query + AI generation)
- **Context Window**: Maintains full conversation history
- **Query Capability**: Can query any subset of 555 shots with complex filters
- **Statistical Accuracy**: Performs real calculations on actual data
- **Cost**: ~$0.001 per query (Gemini 2.0 Flash pricing)

## Advantages Over Current Implementation

| Feature | Current (Gemini API) | New (Vertex AI Agent) |
|---------|---------------------|----------------------|
| Memory | ❌ Stateless | ✅ Multi-turn memory |
| BigQuery Access | ❌ Manual CSV passing | ✅ Direct tool calling |
| Context Management | ❌ Manual prompt engineering | ✅ Automatic |
| Code Execution | ✅ Yes | ❌ No (uses tools instead) |
| Visualizations | ✅ Plotly charts | ❌ Text-only |
| Conversational Flow | ❌ Requires full context each time | ✅ Natural follow-ups |
| Ease of Use | Medium | Easy |

## Future Enhancements

### Phase 2: Cloud Functions Integration
The agent can trigger automated workflows:
```python
# After data import
coach.chat("Analyze today's session and email me a summary")

# Scheduled analysis
coach.chat("Run weekly performance review and post to Slack")
```

### Phase 3: Cloud Run Deployment
Access the agent from anywhere:
```bash
curl -X POST https://golf-coach-api.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze my Driver performance"}'
```

### Phase 4: Streamlit Integration
Add to the AI Coach tab with enhanced features:
- Conversation history sidebar
- "Remember this preference" button
- Export conversation as PDF
- Share coaching session with instructor

## Troubleshooting

### Agent Not Initializing
```python
# Check GCP credentials
import os
print(os.getenv("GCP_PROJECT_ID"))  # Should be: valued-odyssey-474423-g1

# Test BigQuery access
from google.cloud import bigquery
client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
print(client.project)  # Should work without errors
```

### Function Calls Failing
```python
# Test individual tool functions
from vertex_ai_agent import GolfCoachAgent

agent = GolfCoachAgent(project_id="valued-odyssey-474423-g1")
result = agent.get_club_statistics("Driver")
print(result)  # Should return statistics dict
```

### Slow Response Times
- **BigQuery queries**: First query is slower (cold start), subsequent queries are cached
- **Model inference**: Gemini 2.0 Flash is optimized for speed (~2s average)
- **Network latency**: Ensure good internet connection for Vertex AI API calls

## Cost Estimation

Based on typical usage patterns:

### Development/Testing (You, Solo)
- **Queries per day**: ~20
- **Monthly cost**: ~$0.60
- **Annual cost**: ~$7.20

### Production (Multiple Users)
- **Queries per day per user**: ~10
- **Users**: 5-10
- **Monthly cost**: $1.50 - $3.00
- **Annual cost**: $18 - $36

### Scaling (Golf Academy)
- **Students**: 50
- **Queries per student per week**: 20
- **Monthly cost**: ~$120
- **Annual cost**: ~$1,440

## Next Steps

1. **Test the agent** with various questions to explore its capabilities
2. **Create custom workflows** using the Python API for your specific use cases
3. **Consider Phase 2** implementation for automated analysis pipelines
4. **Plan Streamlit integration** when ready for web UI access
5. **Explore Cloud Run deployment** for mobile/multi-device access

## Support

For issues or questions:
1. Check BigQuery connection: `python -c "from vertex_ai_agent import create_golf_coach; create_golf_coach()"`
2. Review error messages in terminal output
3. Verify GCP credentials: `gcloud auth application-default login`
4. Test individual tool functions directly in Python

## Resources

- **Vertex AI Documentation**: https://cloud.google.com/vertex-ai/docs
- **Gemini API Reference**: https://ai.google.dev/gemini-api/docs
- **BigQuery Python Client**: https://cloud.google.com/python/docs/reference/bigquery/latest
- **Function Calling Guide**: https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling

---

**Status**: ✅ Phase 1 Complete - Agent is production-ready for command-line and Python API usage
