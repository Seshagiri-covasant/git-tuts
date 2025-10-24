from flask import request
from marshmallow import ValidationError
from ..schemas import api_schemas
from ..agents.ba_reporter import generate_llm_ba_summary
from ..agents.visualization_generator import generate_chart_config
from ..utils.exceptions import ServiceException
from .chatbot_service import get_chatbot_with_validation, validate_chatbot_status, get_chatbot_db
from .helpers import clear_agent_cache


def configure_llm_service(chatbot_id: str):
    """Configures the LLM for a chatbot. Parses request internally."""
    try:
        data = api_schemas.LLMConfigSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id)
    current_status = chatbot.get("status", "created")
    if current_status not in ["created", "db_configured"]:
        raise ServiceException(
            f"Chatbot must be in 'created' or 'db_configured' status to configure LLM. Current: '{current_status}'", 412)

    db = get_chatbot_db()
    update_params = {
        "chatbot_id": chatbot_id,
        "current_llm_name": data['llm_name'],
        "status": "llm_configured"
    }
    if 'temperature' in data and data['temperature'] is not None:
        update_params["temperature"] = data['temperature']

    print(f"[LLM Service] Configuring LLM for chatbot {chatbot_id}: {data['llm_name']}")
    updated_chatbot = db.update_chatbot(**update_params)
    print(f"[LLM Service] Updated chatbot LLM: {updated_chatbot['current_llm_name']}")
    return {"llm_name": updated_chatbot['current_llm_name'], "temperature": updated_chatbot.get('temperature', 0.7)}


def update_llm_service(chatbot_id: str):
    """Updates the LLM for an already configured chatbot. Parses request internally."""
    try:
        data = api_schemas.LLMConfigSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "llm_configured")

    db = get_chatbot_db()
    old_temperature = chatbot.get("temperature", 0.7)
    temperature_changed = 'temperature' in data and data[
        'temperature'] is not None and data['temperature'] != old_temperature

    update_params = {"chatbot_id": chatbot_id,
                     "current_llm_name": data['llm_name']}
    if 'temperature' in data and data['temperature'] is not None:
        update_params["temperature"] = data['temperature']

    updated_chatbot = db.update_chatbot(**update_params)
    db.db_engine.dispose()

    clear_agent_cache(chatbot_id)

    response = {"llm_name": updated_chatbot['current_llm_name'],
                "temperature": updated_chatbot.get('temperature', 0.7)}
    if temperature_changed:
        response["warning"] = "Temperature has changed. Please re-run the benchmark to get updated results."
        response["benchmark_status"] = "needs_rerun"

    return response


def get_ba_summary_service():
    """Returns BA summary for an interaction: uses cache if available, otherwise generates and stores it.

    Expected payload: { table: [...], prompt: str, chatbot_id: str, interaction_id?: str, regenerate?: bool }
    If interaction_id is provided and regenerate is False/omitted, the cached summary is returned when present.
    If regenerate is True, a new summary is generated and stored.
    """
    try:
        payload = request.get_json() or {}
        validated_data = api_schemas.BAInsightSchema().load(payload)
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    table = validated_data['table']
    prompt = validated_data['prompt']
    llm_name = validated_data.get('llm_name')
    chatbot_id = validated_data.get('chatbot_id')
    interaction_id = request.args.get('interaction_id') or payload.get('interaction_id')
    raw_regen = request.args.get('regenerate') if request.args else payload.get('regenerate')
    regenerate = True if raw_regen in [True, 'true', '1', 1] else False

    db = get_chatbot_db()
    chatbot = db.get_chatbot(chatbot_id)

    current_llm = chatbot.get('current_llm_name')
    current_temperature = chatbot.get('temperature')

    def _generate():
        return generate_llm_ba_summary(table, prompt, chatbot_id, current_llm, current_temperature)

    try:
        if interaction_id and not regenerate:
            summary = db.get_or_generate_ba_summary(interaction_id, _generate)
        else:
            summary = _generate()
            if interaction_id:
                db.update_ba_summary(interaction_id, summary)
        return summary
    except Exception as e:
        raise ServiceException(f"Error generating BA summary: {e}", 500)


def get_visualization_service():
    """Generates a chart configuration for visualization. Parses request internally."""
    try:
        validated_data = api_schemas.VisualizationSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    table = validated_data['table']
    prompt = validated_data['prompt']
    sql_query = validated_data['sql_query']
    chatbot_id = validated_data['chatbot_id']
    
    db = get_chatbot_db()
    chatbot = db.get_chatbot(chatbot_id)
    
    current_llm = chatbot.get('current_llm_name')
    current_temperature = chatbot.get('temperature')

    try:
        return generate_chart_config(table, prompt, sql_query, chatbot_id, current_llm, current_temperature)
    except Exception as e:
        raise ServiceException(f"Error generating chart config: {e}", 500)
