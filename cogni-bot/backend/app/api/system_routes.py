from flask import jsonify
from app.api.routes import app

from ..services import system_service, agent_service, chatbot_service


@app.route('/health')
def health_check():
    """Provides a basic health check of the application and its services."""
    return jsonify(system_service.get_system_status_service())


@app.route('/system/status', methods=['GET'])
def get_system_status():
    """Returns comprehensive system status including memory and DB connections."""
    return jsonify(system_service.get_system_status_service())


@app.route("/clear-agents", methods=["POST"])
def clear_agents():
    """Clears all cached agents from memory."""
    return jsonify(agent_service.clear_all_agents_service())


@app.route("/chatbots/<chatbot_id>/clear-prompt", methods=["POST"])
def clear_chatbot_prompt(chatbot_id):
    """Clears the stored enhanced prompt for a specific chatbot."""
    return jsonify(agent_service.clear_chatbot_prompt_service(chatbot_id))


@app.route("/test-connection", methods=["POST"])
def test_database_connection():
    """
    Validates and tests a set of database connection details.
    All logic is handled by the service layer.
    """
    result = chatbot_service.test_database_connection_service()
    return jsonify(result)
