from flask import jsonify
from app.api.routes import app
from ..services import chatbot_service, llm_service, agent_service
import logging

logger = logging.getLogger(__name__)


@app.route("/chatbots", methods=["GET"])
def get_chatbots():
    return jsonify(chatbot_service.get_all_chatbots_service())


@app.route("/chatbots", methods=["POST"])
def create_chatbot():
    chatbot = chatbot_service.create_chatbot_service()
    return jsonify({
        "message": "Chatbot created successfully",
        "chatbot": chatbot,
        "next_step": "Configure application database using POST /api/chatbots/{chatbot_id}/database"
    }), 201


@app.route("/chatbots/<chatbot_id>", methods=["GET"])
def get_chatbot(chatbot_id):
    return jsonify(chatbot_service.get_chatbot_details_service(chatbot_id))


@app.route("/chatbots/<chatbot_id>", methods=["DELETE"])
def delete_chatbot(chatbot_id):
    return jsonify(chatbot_service.delete_chatbot_service(chatbot_id))


@app.route("/chatbots/<chatbot_id>/database", methods=["POST"])
def configure_chatbot_database(chatbot_id):
    result = chatbot_service.configure_database_service(chatbot_id)
    return jsonify({
        "message": "Application database configured successfully",
        "chatbot_id": chatbot_id,
        "db_type": result.get("db_type"),
        "next_step": "Configure LLM using POST /api/chatbots/{chatbot_id}/llm"
        
    })


@app.route("/chatbots/<chatbot_id>/llm", methods=["POST"])
def configure_chatbot_llm(chatbot_id):
    result = llm_service.configure_llm_service(chatbot_id)
    return jsonify({
        "message": "LLM configured successfully",
        "chatbot_id": chatbot_id,
        **result,
        "next_step": "Configure prompt template or finalize setup."
    })


@app.route("/chatbots/<chatbot_id>/llm", methods=["PUT"])
def update_chatbot_llm(chatbot_id):
    result = llm_service.update_llm_service(chatbot_id)
    return jsonify({
        "message": "LLM configuration updated successfully",
        "chatbot_id": chatbot_id,
        **result
    })


@app.route("/chatbots/<chatbot_id>/schema", methods=["GET"])
def get_chatbot_schema(chatbot_id):
    return jsonify(chatbot_service.get_schema_service(chatbot_id))


@app.route("/chatbots/<chatbot_id>/ready", methods=["POST"])
def set_chatbot_ready(chatbot_id):
    result = chatbot_service.set_chatbot_ready_service(chatbot_id)
    return jsonify({
        "message": "Chatbot is now ready for conversations! Enhanced prompt generated.",
        "chatbot_id": chatbot_id,
        **result,
        "next_step": f"POST /api/chatbots/{chatbot_id}/conversations to start chatting"
    })


@app.route("/chatbots/<chatbot_id>/restart", methods=["POST"])
def restart_chatbot(chatbot_id):
    return jsonify(agent_service.restart_chatbot_service(chatbot_id))


@app.route("/chatbots/<chatbot_id>/database/update-schema", methods=["POST"])
def update_database_schema(chatbot_id):
    return jsonify(chatbot_service.update_database_schema_service(chatbot_id))


@app.route("/chatbots/<chatbot_id>/knowledge-base", methods=["POST"])
def update_knowledge_base_settings(chatbot_id):
    chatbot = chatbot_service.update_knowledge_base_service(chatbot_id)
    return jsonify({"message": "Knowledge base settings updated successfully", "chatbot": chatbot})


@app.route("/chatbots/<chatbot_id>/semantic-schema", methods=["GET"])
def get_chatbot_semantic_schema(chatbot_id):
    """
    Returns the semantic schema for a chatbot.
    """
    semantic_schema = chatbot_service.get_semantic_schema_service(chatbot_id)
    return jsonify({
        "chatbot_id": chatbot_id,
        "semantic_schema": semantic_schema
    })


@app.route("/chatbots/<chatbot_id>/semantic-schema", methods=["PUT"])
def update_chatbot_semantic_schema(chatbot_id):
    """
    Updates the semantic schema for a chatbot.
    """
    try:
        result = chatbot_service.update_semantic_schema_service(chatbot_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Unhandled error in update_chatbot_semantic_schema for {chatbot_id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/chatbots/<chatbot_id>/semantic-schema/export", methods=["GET"])
def export_chatbot_semantic_schema(chatbot_id):
    """
    Exports the semantic schema for a chatbot as CSV.
    """
    try:
        result = chatbot_service.export_semantic_schema_service(chatbot_id)
        return result
    except Exception as e:
        logger.error(f"Unhandled error in export_chatbot_semantic_schema for {chatbot_id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/chatbots/<chatbot_id>/semantic-schema/import", methods=["POST"])
def import_chatbot_semantic_schema(chatbot_id):
    """
    Imports a semantic schema for a chatbot from CSV.
    """
    try:
        result = chatbot_service.import_semantic_schema_service(chatbot_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Unhandled error in import_chatbot_semantic_schema for {chatbot_id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/chatbots/<chatbot_id>/register", methods=["POST"])
def register_chatbot_external_ids(chatbot_id):
    """Attaches external clientId/projectId mapping to a chatbot."""
    result = chatbot_service.register_chatbot_service(chatbot_id)
    return jsonify({"message": "Chatbot registered successfully", **result}), 200