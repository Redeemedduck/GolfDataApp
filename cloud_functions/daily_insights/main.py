"""
Cloud Function: Daily Golf Insights

Triggers:
- Cloud Scheduler (daily at specified time)
- HTTP request (manual trigger)

Functionality:
- Queries BigQuery for recent performance data
- Uses Vertex AI Golf Coach Agent to generate insights
- Optionally sends email summary
- Publishes insights to Pub/Sub for other consumers
"""

import functions_framework
from google.cloud import bigquery, pubsub_v1
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Content, Part
import os
import json
from datetime import datetime, timezone, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'valued-odyssey-474423-g1')
GCP_REGION = os.getenv('GCP_REGION', 'us-central1')
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID', 'golf_data')
BQ_TABLE_ID = os.getenv('BQ_TABLE_ID', 'shots')
BQ_FULL_TABLE_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize clients
bq_client = bigquery.Client(project=GCP_PROJECT_ID)
publisher = pubsub_v1.PublisherClient()
vertexai.init(project=GCP_PROJECT_ID, location=GCP_REGION)


def get_recent_performance_summary(days=7):
    """Get summary statistics for the past N days"""
    query = f"""
    WITH recent_shots AS (
        SELECT *
        FROM `{BQ_FULL_TABLE_ID}`
        WHERE DATE(date_added) >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
          AND carry > 0
    )
    SELECT
        COUNT(*) as total_shots,
        COUNT(DISTINCT session_id) as sessions,
        COUNT(DISTINCT club) as clubs_used,
        STRING_AGG(DISTINCT club ORDER BY club) as clubs_list,
        AVG(carry) as avg_carry,
        AVG(ball_speed) as avg_ball_speed,
        AVG(smash) as avg_smash,
        STDDEV(carry) as carry_consistency,
        MAX(carry) as best_carry,
        MIN(DATE(date_added)) as first_date,
        MAX(DATE(date_added)) as last_date
    FROM recent_shots
    """

    result = bq_client.query(query).to_dataframe()

    if result.empty or result['total_shots'].iloc[0] == 0:
        return None

    return result.iloc[0].to_dict()


def get_club_performance(days=7):
    """Get per-club performance stats"""
    query = f"""
    SELECT
        club,
        COUNT(*) as shots,
        ROUND(AVG(carry), 1) as avg_carry,
        ROUND(STDDEV(carry), 1) as carry_std,
        ROUND(AVG(ball_speed), 1) as avg_ball_speed,
        ROUND(AVG(smash), 2) as avg_smash,
        ROUND(AVG(ABS(side_distance)), 1) as avg_dispersion
    FROM `{BQ_FULL_TABLE_ID}`
    WHERE DATE(date_added) >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
      AND carry > 0
    GROUP BY club
    ORDER BY avg_carry DESC
    """

    result = bq_client.query(query).to_dataframe()
    return result.to_dict(orient='records') if not result.empty else []


def generate_insights_with_gemini(summary, club_stats, days=7):
    """Generate AI insights using Gemini with provided data"""
    from google import genai
    from google.genai import types

    if not GEMINI_API_KEY:
        logger.warning("Gemini API key not configured, skipping AI insights")
        return "AI insights unavailable (API key not configured)"

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Build data context
        data_summary = f"""
**Performance Summary (Last {days} Days)**
- Total Shots: {summary['total_shots']}
- Sessions: {summary['sessions']}
- Clubs Used: {summary['clubs_list']}
- Average Carry: {summary['avg_carry']:.1f} yards
- Average Ball Speed: {summary['avg_ball_speed']:.1f} mph
- Average Smash Factor: {summary['avg_smash']:.2f}
- Carry Consistency (Std Dev): {summary['carry_consistency']:.1f} yards
- Best Shot: {summary['best_carry']:.1f} yards
- Practice Period: {summary['first_date']} to {summary['last_date']}

**Club-by-Club Performance**
"""

        for club in club_stats:
            data_summary += f"\n{club['club']}:"
            data_summary += f"\n  - Shots: {club['shots']}"
            data_summary += f"\n  - Avg Carry: {club['avg_carry']} yards (± {club['carry_std']} yards)"
            data_summary += f"\n  - Ball Speed: {club['avg_ball_speed']} mph"
            data_summary += f"\n  - Smash: {club['avg_smash']}"
            data_summary += f"\n  - Dispersion: {club['avg_dispersion']} yards"

        prompt = f"""You are an expert golf coach providing a daily performance summary and coaching insights.

{data_summary}

**Your Task:**
Analyze this golfer's performance over the past {days} days and provide:

1. **Key Insights** (2-3 bullet points)
   - Notable improvements or concerns
   - Consistency patterns
   - Best performing clubs

2. **Areas for Improvement** (2-3 specific items)
   - What metrics need attention
   - Which clubs need work
   - Technical aspects to focus on

3. **This Week's Focus** (1-2 actionable items)
   - Specific drills or practice priorities
   - Measurable goals for next session

Be encouraging but honest. Keep it concise and actionable. The golfer practices at Denver altitude (5,280 ft).
"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1000
            )
        )

        return response.text

    except Exception as e:
        logger.error(f"Gemini API error: {e}", exc_info=True)
        return f"AI insights temporarily unavailable: {str(e)}"


def publish_insights_event(insights, summary):
    """Publish insights to Pub/Sub for other consumers"""
    try:
        topic_path = publisher.topic_path(GCP_PROJECT_ID, 'golf-analysis-ready')

        message_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'insights': insights,
            'summary': summary,
            'type': 'daily_insights'
        }

        future = publisher.publish(
            topic_path,
            json.dumps(message_data).encode('utf-8')
        )

        future.result()
        logger.info("Published insights event to Pub/Sub")
    except Exception as e:
        logger.warning(f"Could not publish insights event: {e}")


def send_email_summary(insights, summary):
    """Send email summary using SendGrid (optional)"""
    sendgrid_key = os.getenv('SENDGRID_API_KEY')
    notification_email = os.getenv('NOTIFICATION_EMAIL', 'matt@coloradolawclassic.org')

    if not sendgrid_key:
        logger.info("SendGrid not configured, skipping email")
        return

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        subject = f"🏌️ Golf Performance Update - {datetime.now().strftime('%B %d, %Y')}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #4CAF50;">🏌️ Your Golf Performance Update</h2>

            <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3>Quick Stats (Last 7 Days)</h3>
                <ul>
                    <li><strong>{summary['total_shots']}</strong> shots across <strong>{summary['sessions']}</strong> sessions</li>
                    <li>Average carry: <strong>{summary['avg_carry']:.1f} yards</strong></li>
                    <li>Best shot: <strong>{summary['best_carry']:.1f} yards</strong></li>
                    <li>Smash factor: <strong>{summary['avg_smash']:.2f}</strong></li>
                </ul>
            </div>

            <div style="white-space: pre-wrap; line-height: 1.6;">
                {insights}
            </div>

            <p style="margin-top: 30px; color: #666; font-size: 12px;">
                This automated summary was generated by your AI Golf Coach.
                <br>Reply to this email with questions or feedback!
            </p>
        </body>
        </html>
        """

        message = Mail(
            from_email='golf-coach@yourdomain.com',
            to_emails=notification_email,
            subject=subject,
            html_content=html_content
        )

        sg = SendGridAPIClient(sendgrid_key)
        response = sg.send(message)

        logger.info(f"Email sent successfully (status: {response.status_code})")

    except Exception as e:
        logger.warning(f"Could not send email: {e}")


@functions_framework.http
def daily_insights_http(request):
    """
    HTTP-triggered function for manual insights generation

    Usage:
        curl -X POST https://REGION-PROJECT_ID.cloudfunctions.net/daily-insights \\
             -H "Content-Type: application/json" \\
             -d '{"days": 7, "send_email": true}'
    """
    try:
        # Parse request
        request_json = request.get_json(silent=True)
        days = 7
        send_email = False

        if request_json:
            days = request_json.get('days', 7)
            send_email = request_json.get('send_email', False)

        logger.info(f"Generating insights for last {days} days")

        # Get performance data
        summary = get_recent_performance_summary(days=days)

        if summary is None or summary['total_shots'] == 0:
            return {
                'status': 'no_data',
                'message': f'No shots found in the last {days} days',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 200

        club_stats = get_club_performance(days=days)

        # Generate AI insights
        insights = generate_insights_with_gemini(summary, club_stats, days=days)

        # Publish to Pub/Sub
        publish_insights_event(insights, summary)

        # Optionally send email
        if send_email:
            send_email_summary(insights, summary)

        return {
            'status': 'success',
            'insights': insights,
            'summary': {
                'total_shots': int(summary['total_shots']),
                'sessions': int(summary['sessions']),
                'avg_carry': float(summary['avg_carry']),
                'best_carry': float(summary['best_carry']),
                'clubs_used': summary['clubs_list']
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, 200

    except Exception as e:
        logger.error(f"Insights generation failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, 500


@functions_framework.cloud_event
def daily_insights_scheduled(cloud_event):
    """
    Cloud Scheduler-triggered function for automated daily insights

    Scheduled to run daily at a specified time (e.g., 8:00 AM)
    """
    try:
        logger.info("Running scheduled daily insights generation")

        # Get performance data
        summary = get_recent_performance_summary(days=7)

        if summary is None or summary['total_shots'] == 0:
            logger.info("No shots in the last 7 days, skipping insights")
            return

        club_stats = get_club_performance(days=7)

        # Generate AI insights
        insights = generate_insights_with_gemini(summary, club_stats, days=7)

        # Publish to Pub/Sub
        publish_insights_event(insights, summary)

        # Send email (controlled by environment variable)
        if os.getenv('AUTO_SEND_EMAIL', 'false').lower() == 'true':
            send_email_summary(insights, summary)

        logger.info("Daily insights generated successfully")

    except Exception as e:
        logger.error(f"Scheduled insights failed: {e}", exc_info=True)
        raise
