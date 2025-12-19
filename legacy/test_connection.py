#!/usr/bin/env python3
"""
Test connections to Supabase and Google Cloud before running the full pipeline
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_supabase():
    """Test Supabase connection"""
    print("Testing Supabase connection...")

    try:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            print("❌ SUPABASE_URL or SUPABASE_KEY not set")
            print("   Set with: export SUPABASE_URL='...' SUPABASE_KEY='...'")
            return False

        supabase = create_client(url, key)

        # Try to query the shots table
        result = supabase.table("shots").select("shot_id", count="exact").limit(1).execute()

        print(f"✅ Supabase connected! Found {result.count} total shots in database")
        return True

    except ImportError:
        print("❌ supabase package not installed")
        print("   Install with: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def test_bigquery():
    """Test BigQuery connection"""
    print("\nTesting BigQuery connection...")

    try:
        from google.cloud import bigquery

        project_id = os.getenv("GCP_PROJECT_ID", "valued-odyssey-474423-g1")

        client = bigquery.Client(project=project_id)

        # Try a simple query
        query = "SELECT 1 as test"
        result = client.query(query).result()

        print(f"✅ BigQuery connected! Project: {project_id}")
        return True

    except ImportError:
        print("❌ google-cloud-bigquery package not installed")
        print("   Install with: pip install google-cloud-bigquery")
        return False
    except Exception as e:
        print(f"❌ BigQuery connection failed: {e}")
        print("   Make sure you've run: gcloud auth application-default login")
        return False

def test_vertex_ai():
    """Test Vertex AI connection"""
    print("\nTesting Vertex AI connection...")

    try:
        from google.cloud import aiplatform

        project_id = os.getenv("GCP_PROJECT_ID", "valued-odyssey-474423-g1")
        region = os.getenv("GCP_REGION", "us-central1")

        aiplatform.init(project=project_id, location=region)

        print(f"✅ Vertex AI initialized! Project: {project_id}, Region: {region}")
        return True

    except ImportError:
        print("❌ google-cloud-aiplatform package not installed")
        print("   Install with: pip install google-cloud-aiplatform")
        return False
    except Exception as e:
        print(f"❌ Vertex AI connection failed: {e}")
        return False

def main():
    print("="*60)
    print("Connection Test for Golf Data Pipeline")
    print("="*60)

    results = []

    results.append(("Supabase", test_supabase()))
    results.append(("BigQuery", test_bigquery()))
    results.append(("Vertex AI", test_vertex_ai()))

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    all_passed = True
    for service, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{service:20} {status}")
        if not passed:
            all_passed = False

    print("="*60)

    if all_passed:
        print("\n🎉 All connections successful! Ready to run the pipeline.")
        print("\nNext steps:")
        print("  1. python supabase_to_bigquery.py full")
        print("  2. python vertex_ai_analysis.py analyze")
        return 0
    else:
        print("\n⚠️  Some connections failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
