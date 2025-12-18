#!/usr/bin/env python3
"""
Analyze golf shot data using Gemini 3.0 Pro with Native Code Execution
"""
import os
import sys
from google import genai
from google.genai import types
from google.cloud import bigquery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "valued-odyssey-474423-g1")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "golf_data")
BQ_TABLE_ID = os.getenv("BQ_TABLE_ID", "shots")

def get_bigquery_client():
    """Initialize BigQuery client"""
    return bigquery.Client(project=GCP_PROJECT_ID)

def query_raw_data(limit=500):
    """Get raw data for the AI to analyze freely"""
    bq_client = get_bigquery_client()
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"
    
    # We fetch ALL columns so the AI can dig into any metric (spin, apex, path, etc)
    query = f"""
        SELECT * 
        FROM `{table_id}` 
        ORDER BY date_added DESC 
        LIMIT {limit}
    """
    
    print(f"Fetching raw data from BigQuery ({limit} rows max)...")
    df = bq_client.query(query).to_dataframe()
    return df

def analyze_with_gemini_code_interpreter(club=None):
    """
    Passes RAW data to Gemini 3.0 Pro and requests analysis using Code Execution.
    """
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found via dotenv.")
        return

    # 1. Fetch Data
    df = query_raw_data()
    if df.empty:
        print("No data found.")
        return

    # Filter in Python if needed, or let AI do it (AI is better if we give it all ctx)
    if club:
        df = df[df['club'].astype(str).str.contains(club, case=False)]
        if df.empty:
            print(f"No data found for club: {club}")
            return

    # 2. Prepare Data Context (CSV string is efficient for reasoning models)
    csv_data = df.to_csv(index=False)
    
    # 3. Construct Prompt
    prompt = f"""
    You are an expert Golf Data Analyst.
    I have provided a dataset of my golf shots below in CSV format.
    
    Your goal is to use your Python Code Execution capabilities to analyze this data deeply.
    DO NOT just summarize the text. Write and run Python code to calculate sophisticated metrics.
    
    DATASET (CSV):
    ```csv
    {csv_data}
    ```
    
    ANALYSIS REQUESTS:
    1. **Dispersion Analysis**: Calculate the standard deviation of 'side_distance' (lateral) and 'carry' (distance) for each club.
    2. **Correlation**: Is there a correlation between 'club_speed' and 'carry' efficiency (Smash Factor)?
    3. **Consistency**: Which club is my most consistent? Which is my least?
    4. **Recommendations**: based on the stats, what one thing should I work on?
    
    Use the `print()` function in your code execution to output your findings so I can see the math.
    Then summarize your insights in natural language.
    """

    print(f"Sending {len(df)} shots to Gemini 3.0 Pro (with Code Execution enabled)...")
    print("Thinking...\n")

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Enable Code Execution Tool (correct syntax for google-genai SDK)
        response = client.models.generate_content(
            model='gemini-3-pro-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{'code_execution': {}}]
            )
        )
        
        print("="*80)
        print("GEMINI 3.0 DATA SCIENTIST REPORT")
        print("="*80)
        
        # Print the thought process / code (if available in parts) or just text
        # Usually dependencies like 'print' output are in the reasoning parts
        # For simplicity, we print the final text which usually summarizes execution
        print(response.text)
        
        # Optional: Inspect execution result parts if needed
        # for part in response.candidates[0].content.parts:
        #     if part.executable_code: print(f"[Code]:\n{part.executable_code.code}\n")
        #     if part.code_execution_result: print(f"[Output]:\n{part.code_execution_result.output}\n")
            
        print("="*80)

    except Exception as e:
        print(f"Gemini Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_club = sys.argv[1]
        analyze_with_gemini_code_interpreter(club=target_club)
    else:
        analyze_with_gemini_code_interpreter()
