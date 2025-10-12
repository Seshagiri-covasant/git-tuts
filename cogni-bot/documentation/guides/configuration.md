# Configuration

## Environment variables (backend)
See `reference/env-vars.md` for full list. Key groups:
- Chatbot metadata DB: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`
- LLM keys: `COHERE_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, `GEMINI_API_KEY`, `CLAUDE_API_KEY`
- Flask: `FLASK_CONFIG`, `FLASK_RUN_HOST`, `FLASK_RUN_PORT`

## LLM selection
- `llm_factory.get_llm(model_name, temperature)` supports `COHERE`, `OPENAI`, `AZURE`, `GEMINI`, `CLAUDE` (see `constants.LLM_MODELS`).
- Configure per chatbot via `/api/chatbots/{id}/llm`.

## Database configuration per chatbot
- Endpoint: POST `/api/chatbots/{id}/database`
- Body depends on `db_type`:
  - `postgresql`: username, password, host, port, db_name
  - `sqlite`: db_name (creates file `db_name.db`)
  - `bigquery`: project_id, dataset_id, credentials_json
- Validates connection, stores URL, extracts schema, converts to semantic schema JSON, builds knowledge cache.

## Knowledge cache
- Stored in `semantic_knowledge_cache` table keyed by chatbot_id; used by Intent Picker and Context Clipper.

## Limits
- Max interactions per conversation: `constants.MAX_INTERACTIONS_PER_CONVERSATION` (default 10).
