from flask import jsonify, request
from app.api.routes import app
from ..services import settings_service
from ..utils.exceptions import ServiceException
import logging

logger = logging.getLogger(__name__)


@app.route('/settings/ai', methods=['GET'])
def get_ai_settings():
    """Get current AI settings including API key configuration."""
    try:
        llm = request.args.get('llm')
        return jsonify(settings_service.get_ai_settings_service(llm_name=llm))
    except ServiceException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected error in get_ai_settings: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/settings/ai', methods=['POST'])
def update_ai_settings():
    """Update AI settings including API key configuration."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        return jsonify(settings_service.update_ai_settings_service(data))
    except ServiceException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected error in update_ai_settings: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/settings/ai/env-status', methods=['GET'])
def get_env_api_key_status():
    """Check if .env API keys are configured for different LLM providers."""
    try:
        return jsonify(settings_service.get_env_api_key_status_service())
    except ServiceException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected error in get_env_api_key_status: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/settings/ai/chatbot/<chatbot_id>', methods=['GET'])
def get_chatbot_ai_settings(chatbot_id):
    """Get AI settings for a specific chatbot."""
    try:
        llm = request.args.get('llm')
        return jsonify(settings_service.get_chatbot_ai_settings_service(chatbot_id, llm_name=llm))
    except ServiceException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected error in get_chatbot_ai_settings: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/settings/ai/chatbot/<chatbot_id>', methods=['POST'])
def update_chatbot_ai_settings(chatbot_id):
    """Update AI settings for a specific chatbot."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        return jsonify(settings_service.update_chatbot_ai_settings_service(chatbot_id, data))
    except ServiceException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected error in update_chatbot_ai_settings: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/settings/ai/global-key', methods=['GET'])
def copy_global_api_key():
    """Return the full decrypted global API key for the requested LLM (for copy action)."""
    try:
        llm = request.args.get('llm', 'COHERE')
        value = settings_service.get_global_api_key_plain(llm)
        return jsonify({"status": "success", "llm_name": llm.upper(), "global_api_key": value})
    except ServiceException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected error in copy_global_api_key: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/settings/ai/local-key', methods=['GET'])
def copy_local_api_key():
    """Return the full decrypted local API key for the requested chatbot/LLM (for copy action)."""
    try:
        chatbot_id = request.args.get('chatbot_id')
        llm = request.args.get('llm', 'COHERE')
        if not chatbot_id:
            return jsonify({"error": "chatbot_id is required"}), 400
        value = settings_service.get_local_api_key_plain(chatbot_id, llm)
        return jsonify({"status": "success", "llm_name": llm.upper(), "local_api_key": value})
    except ServiceException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected error in copy_local_api_key: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500