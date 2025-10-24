import logging
import json
from flask import request
from marshmallow import ValidationError

from ..schemas import api_schemas
from ..utils.exceptions import ServiceException
from ..utils.monitoring import monitored_database_operation
from .chatbot_service import get_chatbot_with_validation, validate_chatbot_status, get_chatbot_db
from .agent_service import get_agent
from .. import constants


def create_conversation_service(chatbot_id: str):
    """Business logic for creating a new conversation. Parses request internally."""
    try:
        validated_data = api_schemas.ConversationCreateSchema().load(request.get_json())
        conversation_name = validated_data['conversation_name']
        owner = validated_data['owner']
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "ready")

    db = get_chatbot_db()
    return db.create_conversation(
        chatbot_id=chatbot_id,
        conversation_name=conversation_name,
        status="active",
        owner=owner,
        template_id=chatbot.get("template_id"),
        conversationType="DEFAULT"
    )


def get_conversations_for_chatbot_service(chatbot_id: str):
    """Gets all conversations for a specific chatbot."""
    get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()
    return db.get_all_conversations(chatbot_id)


def get_conversation_by_id_service(conversation_id: str):
    """Gets a single conversation by its ID."""
    db = get_chatbot_db()
    conversation = db.get_conversation(conversation_id)
    if not conversation:
        raise ServiceException("Conversation not found", 404)
    return conversation


def delete_conversation_service(conversation_id: str):
    """Deletes a conversation and all its interactions."""
    get_conversation_by_id_service(conversation_id)
    db = get_chatbot_db()
    db.delete_conversation(conversation_id)
    return {"message": "Conversation deleted successfully", "conversation_id": conversation_id}


def create_interaction_service(conversation_id: str):
    """Processes a user request and creates a new interaction. Parses request internally."""
    db = get_chatbot_db()
    # 1. Check the current interaction count BEFORE processing the request.
    current_count = db.get_interaction_count(conversation_id)
    if current_count >= constants.MAX_INTERACTIONS_PER_CONVERSATION:
        raise ServiceException(
            f"Conversation limit of {constants.MAX_INTERACTIONS_PER_CONVERSATION} interactions has been reached.", 403
        )
    try:
        validated_data = api_schemas.InteractionCreateSchema().load(request.get_json())
        request_text = validated_data['request']
        llm_name_override = validated_data.get('llm_name')
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    with monitored_database_operation("get_conversation", "chatbot_main"):
        conversation = get_conversation_by_id_service(conversation_id)

    chatbot_id = conversation.get("chatbotId")
    if not chatbot_id:
        raise ServiceException(
            "Could not find chatbot_id in conversation object.", 500)

    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "ready")

    agent = get_agent(chatbot_id)
    effective_llm_name = llm_name_override or chatbot.get("current_llm_name")
    temperature = chatbot.get("temperature", 0.7)

    agent_response = agent.execute(
        conversation_id, request_text, effective_llm_name, temperature=temperature)
    if not agent_response:
        raise ServiceException("No response from agent", 500)

    # HITL: Check if the agent is asking a clarifying question
    if agent_response.get("question"):
        return {
            "question": agent_response["question"],
            "interaction_type": "clarification"
        }
    
    # HITL: Check if the agent needs human approval
    if agent_response.get("human_approval_needed"):
        return {
            "approval_request": agent_response.get("approval_request", {}),
            "clarification_questions": agent_response.get("clarification_questions", []),
            "similar_columns": agent_response.get("similar_columns", []),
            "ambiguity_analysis": agent_response.get("ambiguity_analysis", {}),
            "interaction_type": "human_approval"
        }

    db = get_chatbot_db()
    with monitored_database_operation("create_interaction", "chatbot_main"):
        interaction = db.create_interaction(
            conversation_id, request_text, agent_response)

    # Handle the response
    return _process_agent_response(agent_response, interaction, db)


def handle_human_approval_service(conversation_id: str):
    """Handles human approval response and continues the workflow."""
    try:
        validated_data = api_schemas.HumanApprovalSchema().load(request.get_json())
        human_response = validated_data['human_response']
        approval_type = validated_data.get('approval_type', 'approval')
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)
    
    with monitored_database_operation("get_conversation", "chatbot_main"):
        conversation = get_conversation_by_id_service(conversation_id)
    
    chatbot_id = conversation.get("chatbotId")
    if not chatbot_id:
        raise ServiceException("Could not find chatbot_id in conversation object.", 500)
    
    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "ready")
    
    agent = get_agent(chatbot_id)
    effective_llm_name = chatbot.get("current_llm_name")
    temperature = chatbot.get("temperature", 0.7)
    
    # Continue the workflow with human response
    agent_response = agent.continue_with_human_approval(
        conversation_id, human_response, effective_llm_name, temperature=temperature)
    
    if not agent_response:
        raise ServiceException("No response from agent after human approval", 500)
    
    # Check if still needs more approval
    if agent_response.get("human_approval_needed"):
        return {
            "approval_request": agent_response.get("approval_request", {}),
            "clarification_questions": agent_response.get("clarification_questions", []),
            "similar_columns": agent_response.get("similar_columns", []),
            "ambiguity_analysis": agent_response.get("ambiguity_analysis", {}),
            "interaction_type": "human_approval"
        }
    
    # Check if needs clarification
    if agent_response.get("question"):
        return {
            "question": agent_response["question"],
            "interaction_type": "clarification"
        }
    
    # Process the final response
    db = get_chatbot_db()
    with monitored_database_operation("create_interaction", "chatbot_main"):
        interaction = db.create_interaction(
            conversation_id, f"Human approval: {human_response.get('type', 'approval')}", agent_response)
    
    # Handle the response similar to create_interaction_service
    return _process_agent_response(agent_response, interaction, db)


def _process_agent_response(agent_response, interaction, db):
    """Helper function to process agent response and handle result storage."""
    try:
        raw = agent_response.get("raw_result_set")
        cleaned_query = agent_response.get("cleaned_query")

        # If AgentManager didn't populate raw_result_set, try to parse JSON from final_result
        if not (isinstance(raw, list) and (len(raw) == 0 or isinstance(raw[0], dict))):
            try:
                fr = agent_response.get("final_result")
                if isinstance(fr, str):
                    import json as _json
                    parsed = _json.loads(fr)
                else:
                    parsed = fr
                # Two supported formats: list of dicts OR { data: [...], metadata: { columns: [...] } }
                if isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
                    raw = parsed.get("data")
                    columns_from_meta = parsed.get("metadata", {}).get("columns")
                elif isinstance(parsed, list):
                    raw = parsed
                    columns_from_meta = None
                else:
                    raw = None
                    columns_from_meta = None
            except Exception:
                raw = None
                columns_from_meta = None

        if isinstance(raw, list) and (len(raw) == 0 or isinstance(raw[0], dict)):
            # Determine columns
            if (len(raw) > 0 and isinstance(raw[0], dict)):
                columns = list(raw[0].keys())
            else:
                columns = columns_from_meta or []

            # Store the result in paged storage
            with monitored_database_operation("store_result", "chatbot_main"):
                db.store_interaction_result(interaction["interactionId"], raw, columns)

        return {
            "interaction_id": interaction["interactionId"],
            "response": agent_response.get("final_result", ""),
            "cleaned_query": cleaned_query,
            "interaction_type": "response"
        }
    except Exception as e:
        logging.error(f"Error processing agent response: {e}")
        return {
            "interaction_id": interaction["interactionId"],
            "response": agent_response.get("final_result", ""),
            "cleaned_query": agent_response.get("cleaned_query", ""),
            "interaction_type": "response",
            "error": str(e)
        }


def get_interactions_paginated_service(conversation_id: str):
    """Gets paginated interactions for a conversation."""
    get_conversation_by_id_service(conversation_id)
    db = get_chatbot_db()
    return db.get_interactions_paginated(conversation_id)


def get_interaction_cleaned_query_service(conversation_id: str, interaction_id: str):
    """Gets the cleaned query for a specific interaction."""
    get_conversation_by_id_service(conversation_id)
    db = get_chatbot_db()
    return db.get_interaction_cleaned_query(interaction_id)


def rate_interaction_service(conversation_id: str, interaction_id: str):
    """Rates an interaction."""
    get_conversation_by_id_service(conversation_id)
    db = get_chatbot_db()
    return db.rate_interaction(interaction_id)


def get_interaction_rating_service(conversation_id: str, interaction_id: str):
    """Gets the rating for a specific interaction."""
    get_conversation_by_id_service(conversation_id)
    db = get_chatbot_db()
    rating = db.get_interaction_rating(conversation_id, interaction_id)
    return rating


def get_conversation_status_service(conversation_id: str):
    """Gets the status of a conversation."""
    conversation = get_conversation_by_id_service(conversation_id)
    return {"status": conversation.get("status", "unknown")}


def get_interaction_result_meta_service(interaction_id: str):
    """Gets metadata for an interaction result."""
    db = get_chatbot_db()
    return db.get_interaction_result_meta(interaction_id)


def get_interaction_result_page_service(interaction_id: str, page: int, page_size: int):
    """Gets a specific page of interaction results."""
    db = get_chatbot_db()
    return db.get_interaction_result_page(interaction_id, page, page_size)


def get_interaction_count_service(conversation_id: str):
    """Gets the count of interactions for a conversation."""
    get_conversation_by_id_service(conversation_id)
    db = get_chatbot_db()
    count = db.get_interaction_count(conversation_id)
    return {"count": count}