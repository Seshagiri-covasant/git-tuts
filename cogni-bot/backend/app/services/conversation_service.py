import logging
import json
from flask import request
from marshmallow import ValidationError
from sqlalchemy import inspect
from ..repositories.app_db_util import AppDbUtil
from uuid import UUID

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


def start_unified_interaction_service():
    """Unified entry point: resolve chatbot via client-id/project-id headers or chatbot_id in body, then process a message.

    Accepts (orchestrator format):
      - Headers: client-id, project-id (kebab-case) OR clientId, projectId (camelCase - backward compatible)
      - Body: { query (or message), thread_id (or conversation_id), chatbot_id? }
    
    Fully compatible with orchestrator API contract.
    """
    from marshmallow import ValidationError
    try:
        payload = request.get_json() or {}
        
        # --- FIX 1: Support BOTH kebab-case and camelCase headers ---
        # Orchestrator sends 'client-id' and 'project-id' (kebab-case)
        # Also support 'clientId'/'projectId' (camelCase) for backward compatibility
        client_id = (
            request.headers.get('client-id') or 
            request.headers.get('clientId') or 
            request.headers.get('Client-Id') or
            payload.get('clientId') or
            payload.get('client-id')
        )
        project_id = (
            request.headers.get('project-id') or 
            request.headers.get('projectId') or 
            request.headers.get('Project-Id') or
            payload.get('projectId') or
            payload.get('project-id')
        )
        
        chatbot_id = payload.get('chatbot_id')
        
        # --- FIX 2: Support BOTH 'query' (orchestrator) and 'message' (legacy) ---
        user_question = payload.get('query') or payload.get('message')
        
        # Optional functional context from orchestrator headers
        module_hdr = request.headers.get('Module')
        submodule_hdr = request.headers.get('Submodule')
        
        # --- FIX 3: Support BOTH 'thread_id' (orchestrator) and 'conversation_id' (legacy) ---
        conversation_id = payload.get('thread_id') or payload.get('conversation_id')

        # Helper: validate UUIDs (ignore placeholders like 'default_thread')
        def _is_valid_uuid(v):
            try:
                UUID(str(v))
                return True
            except Exception:
                return False

        if not user_question or not isinstance(user_question, str) or not user_question.strip():
            raise ValidationError({"query": ["Missing or empty 'query' field."]})

        db = get_chatbot_db()

        # Resolve chatbot_id via mapping if not provided explicitly
        if not chatbot_id:
            if client_id and project_id:
                chatbot_row = db.find_chatbot_by_external_ids(client_id, project_id)
                if not chatbot_row:
                    raise ServiceException("No chatbot mapped for provided client-id/project-id", 404)
                chatbot_id = chatbot_row.get('chatbot_id')
            else:
                raise ServiceException("Request must include client-id/project-id headers or a chatbot_id in the body", 400)

        # Validate chatbot and status
        chatbot = get_chatbot_with_validation(chatbot_id)
        validate_chatbot_status(chatbot, "ready")

        # Ensure conversation exists (create if missing or invalid/nonexistent)
        if not conversation_id or not _is_valid_uuid(conversation_id):
            conv = db.create_conversation(
                chatbot_id=chatbot_id,
                conversation_name=f"Orchestrator Chat: {user_question[:30]}...",
                status="active",
                owner=client_id or "unified_user"
            )
            conversation_id = conv.get("conversationId")
        else:
            try:
                _ = get_conversation_by_id_service(conversation_id)
            except ServiceException:
                conv = db.create_conversation(
                    chatbot_id=chatbot_id,
                    conversation_name=f"Orchestrator Chat: {user_question[:30]}...",
                    status="active",
                    owner=client_id or "unified_user"
                )
                conversation_id = conv.get("conversationId")

        # Quick metadata intent: "what are the tables" (no hardcoded names)
        ql = (user_question or "").strip().lower()
        wants_tables = any(
            phrase in ql for phrase in [
                "what are the tables",
                "what are the table names",
                "list tables",
                "show tables",
                "table names"
            ]
        )

        if wants_tables:
            try:
                # Build a transient connection to application DB using chatbot config
                app_db = AppDbUtil(
                    chatbot.get("db_url"),
                    credentials_json=chatbot.get("credentials_json")
                )
                with app_db.db_engine.connect() as _conn:
                    insp = inspect(app_db.db_engine)
                    schema_name = chatbot.get("schema_name")
                    # Try inspector first
                    try:
                        table_names = insp.get_table_names(schema=schema_name)
                    except Exception:
                        table_names = []

                    # Dialect-specific fallback if inspector yielded nothing
                    if not table_names:
                        try:
                            dialect = app_db.db_engine.dialect.name.lower()
                            if dialect == 'mssql':
                                rs = _conn.exec_driver_sql(
                                    "SELECT t.name FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE s.name = :schema",
                                    {'schema': schema_name or 'dbo'}
                                )
                                table_names = [r[0] for r in rs]
                            elif dialect in ('postgresql', 'mysql'):
                                rs = _conn.exec_driver_sql(
                                    "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema",
                                    {'schema': schema_name or 'public'}
                                )
                                table_names = [r[0] for r in rs]
                        except Exception:
                            table_names = []

                # Persist a synthetic interaction with the table list
                tables_payload = {"data": [{"table": t} for t in sorted(set(table_names))],
                                  "metadata": {"columns": ["table"], "row_count": len(table_names)}}
                agent_response = {
                    "final_result": json.dumps(tables_payload),
                    "cleaned_query": None,
                    "raw_result_set": tables_payload.get("data")
                }

                with monitored_database_operation("create_interaction", "chatbot_main"):
                    interaction = db.create_interaction(conversation_id, user_question, agent_response)

                processed_response = _process_agent_response(agent_response, interaction, db)
                processed_response["thread_id"] = conversation_id
                return processed_response
            except Exception as meta_err:
                # Fall back to normal agent path if metadata lookup fails
                logging.error(f"Metadata tables lookup failed: {meta_err}")

        # Execute via agent for all other cases
        agent = get_agent(chatbot_id)
        effective_llm_name = chatbot.get("current_llm_name")
        temperature = chatbot.get("temperature", 0.7)

        # Mirror Module/Submodule into message context if provided
        if module_hdr or submodule_hdr:
            prefix_parts = []
            if module_hdr:
                prefix_parts.append(f"Module={module_hdr}")
            if submodule_hdr:
                prefix_parts.append(f"Submodule={submodule_hdr}")
            prefix = "[" + "; ".join(prefix_parts) + "] "
            message_for_agent = f"{prefix}{user_question}"
        else:
            message_for_agent = user_question

        agent_response = agent.execute(
            conversation_id, message_for_agent, effective_llm_name, temperature=temperature)
        if not agent_response:
            raise ServiceException("No response from agent", 500)

        # Check for clarification or approval BEFORE processing interaction
        if agent_response.get("question"):
            return {
                "question": agent_response["question"],
                "interaction_type": "clarification",
                "thread_id": conversation_id,  # Return thread_id for orchestrator
            }

        if agent_response.get("human_approval_needed"):
            return {
                "approval_request": agent_response.get("approval_request", {}),
                "clarification_questions": agent_response.get("clarification_questions", []),
                "similar_columns": agent_response.get("similar_columns", []),
                "ambiguity_analysis": agent_response.get("ambiguity_analysis", {}),
                "interaction_type": "human_approval",
                "thread_id": conversation_id,  # Return thread_id for orchestrator
            }

        # Persist interaction and process response
        with monitored_database_operation("create_interaction", "chatbot_main"):
            interaction = db.create_interaction(conversation_id, user_question, agent_response)

        # Process the agent response
        processed_response = _process_agent_response(agent_response, interaction, db)
        
        # --- FIX 4: Return thread_id instead of conversation_id for orchestrator compatibility ---
        # Add thread_id to response for orchestrator
        processed_response["thread_id"] = conversation_id
        
        # Keep conversation_id for backward compatibility with direct API clients
        # Orchestrator should use thread_id, but both are present for flexibility
        
        return processed_response
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)
    except ServiceException:
        raise
    except Exception as e:
        raise ServiceException(f"Failed to process unified interaction: {str(e)}", 500)