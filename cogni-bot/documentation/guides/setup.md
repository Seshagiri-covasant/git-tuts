# Setup & Installation

## Backend
- App factory: `app/factory.py` creates the Flask app, registers `/api` blueprint, configures CORS, executor, logging, and singletons `ChatbotDbUtil`, agent cache, benchmark status.
- Entry point: `backend/main.py` loads env, cleans old BigQuery creds, creates app, and serves.
- Databases:
  - Chatbot metadata: PostgreSQL (from env) via `ChatbotDbUtil`.
  - Application DB (your data): configured per chatbot → PostgreSQL/SQLite/BigQuery via `AppDbUtil`.

## Frontend
- Vite+React in `frontend/`, Axios `src/services/api.ts` targets `http://localhost:5000` in dev.

## Installation steps
- Follow Getting Started for venv, dependencies, and dev servers.
- Ensure PostgreSQL credentials are valid and the user can create/alter tables.

## Verify installation
- GET `/api/health` returns status
- GET `/api/` returns welcome JSON
- Frontend shows chatbot list.
