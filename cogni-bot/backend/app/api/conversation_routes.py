# app/api/conversation_routes.py
from flask import jsonify
from .routes import app
from ..services import conversation_service, llm_service


@app.route("/chatbots/<chatbot_id>/conversations", methods=["POST"])
def create_conversation(chatbot_id):
    conversation = conversation_service.create_conversation_service(chatbot_id)
    return jsonify({
        "message": "Conversation created successfully",
        "conversation": conversation,
        "next_step": "Start interacting using POST /api/conversations/{conversationId}/interactions"
    }), 201


@app.route("/chatbots/<chatbot_id>/conversations", methods=["GET"])
def get_conversations(chatbot_id):
    conversations = conversation_service.get_conversations_for_chatbot_service(
        chatbot_id)
    return jsonify(conversations)


@app.route("/conversations/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    conversation = conversation_service.get_conversation_by_id_service(
        conversation_id)
    return jsonify(conversation)


@app.route("/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    result = conversation_service.delete_conversation_service(conversation_id)
    return jsonify(result)


@app.route("/conversations/<conversation_id>/interactions", methods=["POST"])
def create_interaction(conversation_id):
    result = conversation_service.create_interaction_service(conversation_id)
    return jsonify({"message": "Query processed successfully", **result}), 201


@app.route("/conversations/<conversation_id>/interactions", methods=["GET"])
def get_interactions(conversation_id):
    interactions = conversation_service.get_interactions_paginated_service(
        conversation_id)
    return jsonify(interactions)


@app.route("/conversations/<conversation_id>/interactions/<interaction_id>", methods=["GET"])
def get_interaction_cleaned_query(conversation_id, interaction_id):
    result = conversation_service.get_interaction_cleaned_query_service(
        conversation_id, interaction_id)
    return jsonify(result)


@app.route("/conversations/<conversation_id>/interactions/<interaction_id>/rating", methods=["POST"])
def rate_interaction(conversation_id, interaction_id):
    result = conversation_service.rate_interaction_service(
        conversation_id, interaction_id)
    return jsonify(result)


@app.route("/conversations/<conversation_id>/interactions/<interaction_id>/rating", methods=["GET"])
def get_interaction_rating_route(conversation_id, interaction_id):
    rating = conversation_service.get_interaction_rating_service(
        conversation_id, interaction_id)
    return jsonify({"rating": rating})


@app.route("/conversations/<conversation_id>/status", methods=["GET"])
def get_conversation_status(conversation_id):
    status = conversation_service.get_conversation_status_service(
        conversation_id)
    return jsonify(status)


# --- Result paging endpoints ---
@app.route("/interactions/<interaction_id>/result/meta", methods=["GET"])
def get_interaction_result_meta(interaction_id):
    data = conversation_service.get_interaction_result_meta_service(interaction_id)
    return jsonify(data)


@app.route("/interactions/<interaction_id>/result/pages", methods=["GET"])
def get_interaction_result_page(interaction_id):
    from flask import request
    page = request.args.get("page", 0, type=int)
    data = conversation_service.get_interaction_result_page_service(interaction_id, page)
    return jsonify(data)


@app.route("/ba-insights", methods=["POST"])
def ba_insights():
    summary = llm_service.get_ba_summary_service()
    return jsonify({"summary": summary})


@app.route("/visualize", methods=["POST"])
def visualize():
    chart_config = llm_service.get_visualization_service()
    return jsonify({"chart_config": chart_config})


@app.route("/conversations/<conversation_id>/interaction-count", methods=["GET"])
def get_conversation_interaction_count(conversation_id):
    """
    Gets the total number of interactions for a conversation.
    All logic is handled by the service layer.
    """
    count_data = conversation_service.get_interaction_count_service(
        conversation_id)
    return jsonify(count_data)
