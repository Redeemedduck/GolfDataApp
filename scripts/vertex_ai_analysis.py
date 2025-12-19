#!/usr/bin/env python3
"""
Vertex AI integration for analyzing golf shot data from BigQuery
"""
import os
from google.cloud import bigquery
from google.cloud import aiplatform
from google.oauth2 import service_account
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "golf_data")
BQ_TABLE_ID = os.getenv("BQ_TABLE_ID", "shots")
GCP_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

def get_bigquery_client():
    """Initialize BigQuery client"""
    if not GCP_PROJECT_ID:
        raise ValueError("Please set GCP_PROJECT_ID environment variable")

    if GCP_CREDENTIALS_PATH and os.path.exists(GCP_CREDENTIALS_PATH):
        credentials = service_account.Credentials.from_service_account_file(GCP_CREDENTIALS_PATH)
        return bigquery.Client(project=GCP_PROJECT_ID, credentials=credentials)
    else:
        return bigquery.Client(project=GCP_PROJECT_ID)

def init_vertex_ai():
    """Initialize Vertex AI"""
    if not GCP_PROJECT_ID:
        raise ValueError("Please set GCP_PROJECT_ID environment variable")

    aiplatform.init(project=GCP_PROJECT_ID, location=GCP_REGION)
    print(f"Vertex AI initialized for project {GCP_PROJECT_ID} in region {GCP_REGION}")

def query_shot_data(club=None, session_id=None, limit=None):
    """
    Query shot data from BigQuery with optional filters

    Args:
        club: Filter by club name (e.g., 'Driver', '7 Iron')
        session_id: Filter by session ID
        limit: Maximum number of rows to return
    """
    bq_client = get_bigquery_client()
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"

    query = f"SELECT * FROM `{table_id}`"
    where_clauses = []

    if club:
        where_clauses.append(f"club = '{club}'")
    if session_id:
        where_clauses.append(f"session_id = '{session_id}'")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY date_added DESC"

    if limit:
        query += f" LIMIT {limit}"

    print(f"Running query: {query}")
    df = bq_client.query(query).to_dataframe()
    print(f"Retrieved {len(df)} shots")

    return df

def analyze_club_performance(club=None):
    """
    Analyze performance metrics for a specific club or all clubs

    Returns key statistics and insights for Vertex AI analysis
    """
    df = query_shot_data(club=club)

    if df.empty:
        print("No data found")
        return None

    # Group by club if analyzing all clubs
    if club is None:
        grouped = df.groupby('club')
    else:
        grouped = df.groupby('shot_type')

    # Calculate statistics
    stats = grouped.agg({
        'carry': ['mean', 'std', 'min', 'max'],
        'total': ['mean', 'std', 'min', 'max'],
        'smash': ['mean', 'std'],
        'ball_speed': ['mean', 'std'],
        'club_speed': ['mean', 'std'],
        'back_spin': ['mean', 'std'],
        'side_spin': ['mean', 'std'],
        'launch_angle': ['mean', 'std'],
        'apex': ['mean', 'std'],
        'shot_id': 'count'
    }).round(2)

    print("\nPerformance Statistics:")
    print(stats)

    return stats

def create_analysis_prompt(club=None, session_id=None):
    """
    Create a comprehensive analysis prompt for Vertex AI based on shot data

    This generates a natural language summary of the data that can be fed to
    Vertex AI's Generative AI models (Gemini) for insights
    """
    df = query_shot_data(club=club, session_id=session_id)

    if df.empty:
        return "No shot data available for analysis."

    # Calculate summary statistics
    total_shots = len(df)
    clubs_used = df['club'].unique().tolist() if not club else [club]

    prompt = f"""
Analyze the following golf shot data from a high-altitude environment (Denver):

SUMMARY:
- Total shots: {total_shots}
- Clubs used: {', '.join(clubs_used)}
- Date range: {df['date_added'].min()} to {df['date_added'].max()}

KEY METRICS (averages):
"""

    for club_name in clubs_used:
        club_data = df[df['club'] == club_name]

        if club_data.empty:
            continue

        prompt += f"\n{club_name}:"
        prompt += f"\n  - Shots: {len(club_data)}"
        prompt += f"\n  - Carry: {club_data['carry'].mean():.1f} ± {club_data['carry'].std():.1f} yards"
        prompt += f"\n  - Total: {club_data['total'].mean():.1f} ± {club_data['total'].std():.1f} yards"
        prompt += f"\n  - Ball Speed: {club_data['ball_speed'].mean():.1f} ± {club_data['ball_speed'].std():.1f} mph"
        prompt += f"\n  - Club Speed: {club_data['club_speed'].mean():.1f} ± {club_data['club_speed'].std():.1f} mph"
        prompt += f"\n  - Smash Factor: {club_data['smash'].mean():.2f} ± {club_data['smash'].std():.2f}"
        prompt += f"\n  - Launch Angle: {club_data['launch_angle'].mean():.1f}° ± {club_data['launch_angle'].std():.1f}°"
        prompt += f"\n  - Back Spin: {club_data['back_spin'].mean():.0f} ± {club_data['back_spin'].std():.0f} rpm"
        prompt += f"\n  - Side Spin: {club_data['side_spin'].mean():.0f} ± {club_data['side_spin'].std():.0f} rpm"
        prompt += f"\n  - Attack Angle: {club_data['attack_angle'].mean():.1f}° ± {club_data['attack_angle'].std():.1f}°"
        prompt += f"\n  - Club Path: {club_data['club_path'].mean():.1f}° ± {club_data['club_path'].std():.1f}°"
        prompt += f"\n  - Face Angle: {club_data['face_angle'].mean():.1f}° ± {club_data['face_angle'].std():.1f}°"

    prompt += """

ANALYSIS REQUESTS:
1. Identify strengths and weaknesses in the swing mechanics
2. Detect any shot dispersion patterns (consistency issues)
3. Recommend specific areas for improvement based on the data
4. Compare metrics against PGA Tour averages (accounting for high altitude)
5. Identify any correlations between club path, face angle, and shot outcome
6. Suggest optimal launch conditions for each club

Please provide actionable insights and specific recommendations.
"""

    return prompt

def analyze_with_gemini(prompt_text):
    """
    Send analysis prompt to Vertex AI Gemini model for insights

    This uses Google's Generative AI (Gemini) via Vertex AI
    """
    try:
        from vertexai.generative_models import GenerativeModel

        init_vertex_ai()

        # Initialize Gemini model
        model = GenerativeModel("gemini-1.5-pro")

        print("Sending prompt to Gemini for analysis...")
        response = model.generate_content(prompt_text)

        print("\n" + "="*70)
        print("VERTEX AI ANALYSIS (Gemini)")
        print("="*70)
        print(response.text)
        print("="*70)

        return response.text

    except ImportError:
        print("Error: vertexai package not installed")
        print("Install with: pip install google-cloud-aiplatform")
        return None
    except Exception as e:
        print(f"Error analyzing with Gemini: {e}")
        return None

def export_for_vertex_ai_training(output_path="golf_data_for_training.csv"):
    """
    Export cleaned data suitable for training custom Vertex AI models

    This creates a CSV with all shot data, properly formatted for ML training
    """
    df = query_shot_data()

    # Clean data for ML
    # Drop image columns (not useful for tabular ML)
    df = df.drop(columns=['impact_img', 'swing_img'], errors='ignore')

    # Handle missing values
    df = df.fillna(0)

    # Add derived features
    df['spin_axis'] = (df['side_spin'] / df['back_spin']).replace([float('inf'), -float('inf')], 0)
    df['face_to_path'] = df['face_angle'] - df['club_path']
    df['efficiency'] = (df['carry'] / df['ball_speed']).replace([float('inf'), -float('inf')], 0)

    # Export
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} shots to {output_path} for Vertex AI training")

    return output_path

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python vertex_ai_analysis.py stats [club_name]         - Show performance statistics")
        print("  python vertex_ai_analysis.py analyze [club_name]       - Analyze with Gemini AI")
        print("  python vertex_ai_analysis.py export                    - Export data for ML training")
        sys.exit(1)

    command = sys.argv[1]

    if command == "stats":
        club = sys.argv[2] if len(sys.argv) > 2 else None
        analyze_club_performance(club)

    elif command == "analyze":
        club = sys.argv[2] if len(sys.argv) > 2 else None
        prompt = create_analysis_prompt(club=club)
        print("\nGenerated Analysis Prompt:")
        print(prompt)
        print("\n" + "="*70 + "\n")
        analyze_with_gemini(prompt)

    elif command == "export":
        export_for_vertex_ai_training()

    else:
        print(f"Unknown command: {command}")
