import logging
from flask import current_app


def extract_bigquery_info(db_url: str, db_type: str) -> dict | None:
    """
    Extracts BigQuery project and dataset IDs from a URL.
    This is a stateless helper function.
    """
    if db_type != "bigquery" or not db_url or not db_url.startswith("bigquery://"):
        return None
    try:
        parts = db_url.replace("bigquery://", "").split("/")
        if len(parts) == 2:
            return {"project_id": parts[0], "dataset_id": parts[1]}
    except Exception:
        pass
    return None


def clear_agent_cache(chatbot_id: str):
    """
    Clears a specific agent from the in-memory cache.
    This function depends on the Flask app context.
    """
    agent_key = f"agent_{chatbot_id}"
    agents_cache = current_app.config.get('AGENTS_CACHE', {})
    if agent_key in agents_cache:
        del agents_cache[agent_key]
        logging.info(f"Cleared agent cache for chatbot {chatbot_id}")
