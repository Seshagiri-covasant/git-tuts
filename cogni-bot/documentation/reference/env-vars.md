# Environment Variables

## Chatbot metadata database (PostgreSQL)
- DB_USER
- DB_PASSWORD
- DB_HOST
- DB_PORT
- DB_NAME

## Flask
- FLASK_CONFIG (default, production)
- FLASK_RUN_HOST (default 127.0.0.1)
- FLASK_RUN_PORT (default 5000)

## LLM providers
- COHERE_API_KEY
- OPENAI_API_KEY
- AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION
- GEMINI_API_KEY
- CLAUDE_API_KEY

## Misc
- Logging is configured in `app/utils/monitoring.py`
- Instance path for checkpoints: `backend/instance/checkpoints`
