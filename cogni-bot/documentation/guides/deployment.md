# Deployment (Implemented Behavior)

This page describes how the repository runs today.

## Running the backend
- `backend/main.py` loads environment variables, performs credential-file cleanup, creates the Flask app via `create_app`, and runs the built-in Flask server using `app.run()` when invoked directly. Host and port can be provided via `FLASK_RUN_HOST` and `FLASK_RUN_PORT`.

## Reverse proxy / WSGI
- The repository includes an `nginx.conf` file in the project root. There is no WSGI runner configuration in the repo; the codebase itself does not start Gunicorn or similar.

## Frontend
- The frontend is a Vite app under `frontend/`. Development server is started with `npm run dev`; a production build can be created with `npm run build`. The codebase does not include a production static server configuration.

## Database migrations
- `ChatbotDbUtil.initialize_tables()` creates required tables if missing.
- `ChatbotDbUtil.migrate_schema()` performs additive column migrations for existing tables (e.g., adds new columns on startup when absent).
