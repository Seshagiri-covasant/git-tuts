# Security (Implemented Behavior)

This page documents only what the codebase currently does.

## Secrets and environment
- LLM and database credentials are read from environment variables via `dotenv` in `backend/main.py` and `app/agents/llm_factory.py`.

## BigQuery credentials handling
- When a chatbot is configured with BigQuery, `AppDbUtil` writes the provided `credentials_json` to a deterministic temp file under `backend/app/repositories/temp_creds/` and sets `GOOGLE_APPLICATION_CREDENTIALS` to that file path.
- On process start, `cleanup_old_credential_files()` is called to remove stale files older than a configured age (default 24 hours). A shutdown handler attempts a final cleanup.

## CORS
- CORS is enabled via `flask_cors.CORS()` initialization in `app/factory.py`.

## Database access
- All application DB access is through SQLAlchemy (`AppDbUtil` for target DB, `ChatbotDbUtil` for metadata DB). The metadata DB is PostgreSQL using credentials from environment variables.

## Agent/cache persistence
- Agent checkpoints are stored in SQLite files under `backend/instance/checkpoints/agent_<chatbot_id>.db`.
- In-memory agent instances are cached in `current_app.config['AGENTS_CACHE']` keyed per chatbot.

No additional security mechanisms are implemented in code beyond the items listed above.
