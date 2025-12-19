#!/usr/bin/env python3
from google.cloud import bigquery

client = bigquery.Client(project='valued-odyssey-474423-g1')
query = """
SELECT DISTINCT club 
FROM `valued-odyssey-474423-g1.golf_data.shots` 
ORDER BY club
"""
df = client.query(query).to_dataframe()
print("Available clubs in BigQuery:")
print(df)
