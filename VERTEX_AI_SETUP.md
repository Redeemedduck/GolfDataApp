# Vertex AI Integration Guide

To analyze your Supabase data with **Google Vertex AI** (e.g. Gemini in Vertex Agent Builder), you have two main paths:

## Option 1: Vertex AI Agent Builder (Data Store)
The easiest way is to sync your data to BigQuery or Cloud Storage, then index it.

1.  **Export Data**:
    -   You can export your `shots` table to CSV from the Supabase Dashboard.
    -   Or write a script to dump it to a Google Cloud Storage bucket (JSON/CSV).
2.  **Create Data Store**:
    -   Go to **Vertex AI Agent Builder** in Google Cloud Console.
    -   Create a new **Data Store**.
    -   Source: **Cloud Storage** (select your exported CSV/JSON).
3.  **Create App**:
    -   Create a "Search" or "Chat" app linked to that Data Store.
    -   You can now query your data using Gemini.

## Option 2: Direct Postgres Extension (pgvector)
Supabase supports `pgvector` which is compatible with many AI tools, but direct connection to Vertex Vector Search usually requires an intermediary (like a pipeline to sync embeddings).

## Option 3: Supabase Wrapper (Foreign Data Wrapper)
If you have a Google Cloud Project project:
1.  Supabase provides wrappers to query external data, but going FROM Vertex TO Postgres is usually done via **Federated Queries** in BigQuery.
2.  **BigQuery Connection**:
    -   In BigQuery, create a **Connection** to Cloud SQL (Postgres).
    -   Wait, Supabase is external. You can use **BigQuery Omni** or simply export/import for analysis.

## Recommended Path for this App:
**Use Option 1 (Export to GCS)**.
Since your data volume is small (<10k shots), a nightly export to GCS that Vertex AI indexes is the most robust and simplest method.

### Automation Script (Conceptual)
You can add a script to `golf_scraper.py` or a new cron job:
```python
# pseudo-code
df = golf_db.get_session_data()
df.to_csv("gs://your-bucket/golf_data.csv")
```
Then Vertex AI will automatically ingest it if configured.
