# Scaling & Performance (Implemented Behavior)

This page describes how the system behaves today according to the codebase.

## Application server
- The Flask app is created via `app/factory.create_app`. The repository does not include a production WSGI setup script; `backend/main.py` runs the development server using `app.run()` when executed directly.

## Database engines and pooling
- `ChatbotDbUtil` and `AppDbUtil` create SQLAlchemy engines using `config.create_database_engine` and pool settings returned by `get_chatbot_db_pool_config` / `get_app_db_pool_config`.

## Agent caching
- Agent instances are stored in `current_app.config['AGENTS_CACHE']` and reused per chatbot until cleared via `/api/clear-agents` or chatbot-specific cache clear paths.

## Checkpointing
- LangGraph checkpoints are persisted in SQLite files under `backend/instance/checkpoints/` one per chatbot.

## Prompt/context sizing
- Intent Picker and Context Clipper limit prompt size by:
  - Scoring tables/columns against question keywords and selecting a subset
  - Hard limits for counts in the overview and relationships included in Query Generator

These are the mechanisms present in the current codebase.
