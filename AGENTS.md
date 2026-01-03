# Repository Guidelines

## Project Structure & Module Organization
- `app.py` is the Streamlit entry point; `pages/` holds multi-page UI modules (use numeric prefixes like `1_...` for ordering).
- `components/` contains reusable chart/table widgets; `services/` is reserved for shared service clients.
- Data pipeline scripts live in `scripts/` (Supabase, BigQuery, Vertex AI, automation).
- Local artifacts: `golf_stats.db` (SQLite), `media/` and `media_cache/` for images, `logs/` for sync logs.
- Deployment assets include `Dockerfile`, `cloudbuild.yaml`, and `cloud_functions/`.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate` create/activate the virtualenv.
- `pip install -r requirements.txt` install local runtime dependencies.
- `streamlit run app.py` run the dashboard locally.
- `python scripts/migrate_to_supabase.py` migrate SQLite shots to Supabase.
- `python scripts/supabase_to_bigquery.py incremental` sync Supabase to BigQuery.
- `python scripts/vertex_ai_analysis.py analyze "7 Iron"` run the AI analysis workflow.

## Coding Style & Naming Conventions
- Python code uses 4-space indentation, snake_case for functions/variables, and PascalCase for classes.
- Keep modules small and focused; place UI-only logic in `pages/` or `components/`.
- No formatter/linter is configured; keep diffs clean and avoid mixed line endings.

## Testing Guidelines
- Run tests with `python -m unittest discover -s tests`.
- Validate UI changes by running the Streamlit app and the relevant scripts.

## Commit & Pull Request Guidelines
- Follow the existing conventional commit style seen in history, e.g., `feat: add BigQuery sync` or `docs: update setup guide`.
- PRs should include a short summary, manual test steps, and screenshots for UI changes.
- Link related issues/tasks and note any required env var changes.

## Configuration & Secrets
- Use `.env` (see `.env.example`) for Supabase and GCP settings; never commit secrets.
- Keep local credentials outside the repo and reference them via `GOOGLE_APPLICATION_CREDENTIALS`.
- Optional: set `USE_SUPABASE_READS=1` to prefer Supabase reads (useful in containers).
