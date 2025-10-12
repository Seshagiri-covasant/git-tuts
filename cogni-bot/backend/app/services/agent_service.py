import os
import sqlite3
import logging
from flask import current_app
from langgraph.checkpoint.sqlite import SqliteSaver

from ..repositories.app_db_util import AppDbUtil
from ..models.enums import ChatbotStatus
from ..utils.exceptions import ServiceException
from ..agents.agent_manager import AgentManager
from ..agents.llm_factory import get_llm
from .chatbot_service import get_chatbot_with_validation, validate_chatbot_status, get_chatbot_db
from .helpers import extract_bigquery_info, clear_agent_cache


def get_agent(chatbot_id: str) -> AgentManager:
    """Gets or creates an agent for a chatbot, managing the cache."""
    agents_cache = current_app.config.get('AGENTS_CACHE', {})
    agent_key = f"agent_{chatbot_id}"

    if agent_key not in agents_cache:
        logging.info(f"Creating new agent for chatbot {chatbot_id}")
        try:
            chatbot = get_chatbot_with_validation(chatbot_id)
            validate_chatbot_status(chatbot, "ready")

            instance_path = current_app.instance_path
            checkpoints_dir = os.path.join(instance_path, 'checkpoints')
            os.makedirs(checkpoints_dir, exist_ok=True)

            checkpoint_filename = os.path.join(
                checkpoints_dir, f"agent_{chatbot_id}.db")
            conn = sqlite3.connect(checkpoint_filename,
                                   check_same_thread=False)
            checkpoint = SqliteSaver(conn)

            chatbot_db = get_chatbot_db()
            app_db = AppDbUtil(
                chatbot["db_url"], credentials_json=chatbot.get("credentials_json"))

            stored_prompt = chatbot_db.get_chatbot_prompt(chatbot_id)
            if not stored_prompt or not stored_prompt.get('prompt'):
                raise ServiceException(
                    "Enhanced prompt not found for this chatbot.", 500)
            template = stored_prompt['prompt']

            temperature = chatbot.get("temperature", 0.7)
            bigquery_info = extract_bigquery_info(
                chatbot.get("db_url"), chatbot.get("db_type"))

            agent_manager = AgentManager(
                db_util=app_db,
                checkpoint=checkpoint,
                template=template,
                temperature=temperature,
                bigquery_info=bigquery_info,
                chatbot_db_util=chatbot_db,
                chatbot_id=chatbot_id
            )
            agents_cache[agent_key] = agent_manager
            logging.info(
                f"Successfully created agent for chatbot {chatbot_id}")
        except Exception as e:
            logging.error(
                f"Failed to initialize agent for chatbot {chatbot_id}: {e}", exc_info=True)
            raise ServiceException(
                f"Failed to initialize agent: {str(e)}", 500)

    return agents_cache[agent_key]


def clear_all_agents_service():
    """Clears the entire agent cache."""
    current_app.config.get('AGENTS_CACHE', {}).clear()
    logging.info("Cleared all cached agents.")
    return {"message": "All agents cleared successfully"}


def restart_chatbot_service(chatbot_id: str):
    """Restarts a chatbot by clearing its agent from the cache."""
    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "ready")
    clear_agent_cache(chatbot_id)
    return {
        "message": "Chatbot restarted successfully with updated configurations",
        "chatbot_id": chatbot_id,
        "note": "Previous conversation history has been preserved"
    }


def clear_chatbot_prompt_service(chatbot_id: str):
    """Clears the stored enhanced prompt for a chatbot."""
    get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()
    db.delete_chatbot_prompt(chatbot_id)
    clear_agent_cache(chatbot_id)
    return {"message": "Chatbot prompt cleared successfully"}
