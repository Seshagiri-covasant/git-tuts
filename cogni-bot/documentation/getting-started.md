# Getting Started

This guide helps you install, configure, and run CogniBot locally.

## Prerequisites
- Python 3.10+
- Node 18+
- PostgreSQL instance for chatbot metadata (configured by env). Target DB can be PostgreSQL/SQLite/BigQuery.

## Backend setup
```bash
cd cogni-bot/backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # create and fill values
python main.py
```
The API serves at `http://localhost:5000/api`.

### Required environment variables
See `documentation/reference/env-vars.md` for the full list. Minimum:
- DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME (PostgreSQL for chatbot metadata)
- Optional LLM keys: COHERE_API_KEY, OPENAI_API_KEY, AZURE_OPENAI_API_KEY, GEMINI_API_KEY, CLAUDE_API_KEY

## Frontend setup
```bash
cd cogni-bot/frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173` and proxies to `http://localhost:5000` in dev.

## Quickstart workflow
1. Create a chatbot: POST `/api/chatbots` with `{ name, temperature? }`.
2. Configure application database: POST `/api/chatbots/{id}/database` with db details.
3. Configure LLM: POST `/api/chatbots/{id}/llm` with `{ llm_name, temperature? }`.
4. Mark ready: POST `/api/chatbots/{id}/ready` (generates enhanced prompt and caches agent).
5. Create conversation: POST `/api/chatbots/{id}/conversations`.
6. Send interactions: POST `/api/conversations/{conversationId}/interactions`.

## Troubleshooting
- Health: GET `/api/health`
- Clear agents: POST `/api/clear-agents`
- Logs: `backend/logs/app.log`
- DB creds for BigQuery are written to `backend/app/repositories/temp_creds` with cleanup on startup.
