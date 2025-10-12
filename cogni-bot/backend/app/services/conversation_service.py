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

    db = get_chatbot_db()
    with monitored_database_operation("create_interaction", "chatbot_main"):
        interaction = db.create_interaction(
            conversation_id, request_text, agent_response)

    # Persist large table results in paged storage (do not alter QueryExecutor; run once per question)
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
                # fallback to metadata columns if available
                columns = columns_from_meta or []

            total_rows = len(raw)
            page_size = 500  # default page size

            # Store result meta
            with db.db_engine.begin() as conn:
                conn.execute(
                    db.interaction_results_table.insert().values(
                        interaction_id=interaction["interactionId"],
                        total_rows=total_rows,
                        total_columns=len(columns),
                        columns_json=json.dumps(columns),
                        page_size=page_size
                    )
                )

            # Page and store
            import gzip, base64, json as _json
            for page_index in range((total_rows + page_size - 1)//page_size):
                start = page_index*page_size
                end = min(start+page_size, total_rows)
                chunk = raw[start:end]
                payload = _json.dumps(chunk)
                compressed = base64.b64encode(gzip.compress(payload.encode('utf-8'))).decode('ascii')
                with db.db_engine.begin() as conn:
                    conn.execute(
                        db.interaction_result_pages_table.insert().values(
                            interaction_id=interaction["interactionId"],
                            page_index=page_index,
                            row_start=start,
                            row_end=end,
                            rows_gzip_base64=compressed
                        )
                    )
    except Exception as _e:
        logging.warning(f"Failed to persist paged results for interaction {interaction.get('interactionId')}: {_e}")

    # Return summary meta but not the heavy rows
    result_meta = None
    if isinstance(agent_response.get("raw_result_set"), list):
        result_meta = {
            "interaction_id": interaction["interactionId"],
            "total_rows": len(agent_response["raw_result_set"]),
            "page_size": 500
        }

    return {
        "interaction": interaction,
        "final_result": agent_response.get("final_result"),
        "cleaned_query": agent_response.get("cleaned_query"),
        "result_meta": result_meta,
        "ba_summary": agent_response.get("ba_summary")
    }

def get_interaction_result_meta_service(interaction_id: str):
    db = get_chatbot_db()
    with db.db_engine.connect() as conn:
        row = conn.execute(db.interaction_results_table.select().where(
            db.interaction_results_table.c.interaction_id == interaction_id
        )).fetchone()
        if not row:
            # Check if the interaction exists at all
            interaction_row = conn.execute(db.interactions_table.select().where(
                db.interactions_table.c.interaction_id == interaction_id
            )).fetchone()
            if not interaction_row:
                raise ServiceException("Interaction not found", 404)
            # Interaction exists but no results stored (likely no tabular data)
            return {
                "interaction_id": interaction_id,
                "total_rows": 0,
                "total_columns": 0,
                "columns": [],
                "page_size": 500,
                "has_tabular_data": False
            }
        data = dict(row._mapping)
        data["columns"] = json.loads(data.pop("columns_json"))
        data["has_tabular_data"] = True
        return data


def get_interaction_result_page_service(interaction_id: str, page: int):
    db = get_chatbot_db()
    with db.db_engine.connect() as conn:
        row = conn.execute(
            db.interaction_result_pages_table.select().where(
                db.interaction_result_pages_table.c.interaction_id == interaction_id,
                db.interaction_result_pages_table.c.page_index == page
            )
        ).fetchone()
        if not row:
            # Check if the interaction exists and has any results
            meta_row = conn.execute(db.interaction_results_table.select().where(
                db.interaction_results_table.c.interaction_id == interaction_id
            )).fetchone()
            if not meta_row:
                # Check if interaction exists at all
                interaction_row = conn.execute(db.interactions_table.select().where(
                    db.interactions_table.c.interaction_id == interaction_id
                )).fetchone()
                if not interaction_row:
                    raise ServiceException("Interaction not found", 404)
                # Interaction exists but no tabular data - return empty page
                return {
                    "page_index": page,
                    "row_start": 0,
                    "row_end": 0,
                    "rows": []
                }
            raise ServiceException("Page not found", 404)
        import gzip, base64, json as _json
        b64 = row._mapping["rows_gzip_base64"]
        rows = _json.loads(gzip.decompress(base64.b64decode(b64)).decode('utf-8'))
        return {
            "page_index": row._mapping["page_index"],
            "row_start": row._mapping["row_start"],
            "row_end": row._mapping["row_end"],
            "rows": rows
        }


def get_interactions_paginated_service(conversation_id: str):
    """Gets a paginated list of interactions and includes conversation limit status."""
    get_conversation_by_id_service(conversation_id)
    limit = request.args.get("limit", 5, type=int)
    offset = request.args.get("offset", 0, type=int)
    db = get_chatbot_db()

    paginated_result = db.get_interactions_paginated(
        conversation_id, limit, offset)

    # 1. Get the current interaction count.
    current_count = paginated_result['total_count']
    limit = constants.MAX_INTERACTIONS_PER_CONVERSATION
    remaining = limit - current_count

    # 2. Add a status object to the response.
    paginated_result['limit_status'] = {
        'current_count': current_count,
        'max_allowed': limit,
        'remaining': remaining,
        'is_at_limit': remaining <= 0
    }

    # 3. Add a user-friendly warning message when they are close to the limit.
    warning_message = None
    if remaining <= 0:
        warning_message = f"This conversation has reached its limit of {limit} messages."
    elif remaining == 1:
        warning_message = "You have 1 message remaining in this conversation."
    elif remaining <= 3:  # Give a heads-up a bit earlier
        warning_message = f"You have {remaining} messages remaining in this conversation."

    paginated_result['limit_status']['warning_message'] = warning_message

    return paginated_result


def get_interaction_cleaned_query_service(conversation_id: str, interaction_id: str):
    """Gets the cleaned SQL query for a specific interaction."""
    db = get_chatbot_db()
    result = db.get_interaction_cleaned_query(conversation_id, interaction_id)
    if result is None:
        raise ServiceException(
            "Interaction not found or no cleaned query exists", 404)
    return result


def rate_interaction_service(conversation_id: str, interaction_id: str):
    """Rates a specific interaction. Parses request internally."""
    try:
        validated_data = api_schemas.InteractionRatingSchema().load(request.get_json())
        rating = validated_data['rating']
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    get_conversation_by_id_service(conversation_id)
    db = get_chatbot_db()

    success = db.update_interaction_rating(
        conversation_id, interaction_id, rating)
    if not success:
        raise ServiceException("Interaction not found", 404)

    return {"message": "Rating updated successfully", "rating": rating}


def get_interaction_rating_service(conversation_id: str, interaction_id: str):
    """Gets the rating for a specific interaction."""
    get_conversation_by_id_service(conversation_id)
    db = get_chatbot_db()
    return db.get_interaction_rating(conversation_id, interaction_id)


def get_conversation_status_service(conversation_id: str):
    """Gets the agent's real-time processing status for a given conversation."""
    db = get_chatbot_db()
    conversation = db.get_conversation(conversation_id)
    if not conversation:
        raise ServiceException("Conversation not found", 404)

    chatbot_id = conversation.get("chatbotId")
    if not chatbot_id:
        raise ServiceException(
            "Chatbot ID not found for this conversation", 500)

    try:
        agent = get_agent(chatbot_id)
        return agent.get_processing_status()
    except ServiceException as e:
        logging.warning(
            f"Agent not ready for status check on conversation {conversation_id}: {e}")
        return {"current_step": "not_ready", "progress": 0, "message": "Agent not ready for processing"}
    except Exception as e:
        logging.error(
            f"Error getting agent status for conversation {conversation_id}: {e}", exc_info=True)
        raise ServiceException(f"Error getting agent status: {e}", 500)


def get_interaction_count_service(conversation_id: str):
    """
    Gets the interaction count and limit status for a conversation.
    Parses request args internally to validate chatbot ownership.
    """
    db = get_chatbot_db()

    # 1. Validate that the conversation exists
    conversation = get_conversation_by_id_service(conversation_id)

    # 2. Validate that the request is for the correct chatbot
    chatbot_id_from_request = request.args.get("chatbot_id")
    if not chatbot_id_from_request:
        raise ServiceException("chatbot_id query parameter is required", 400)

    if conversation.get("chatbotId") != chatbot_id_from_request:
        raise ServiceException(
            "Conversation does not belong to the specified chatbot", 403)  # 403 Forbidden

    # 3. Get the current count from the database
    current_count = db.get_interaction_count(conversation_id)
    limit = constants.MAX_INTERACTIONS_PER_CONVERSATION

    # 4. Return the data dictionary
    return {
        "conversation_id": conversation_id,
        "interaction_count": current_count,
        "max_interactions": limit
    }
