import logging
from flask import request
from marshmallow import ValidationError

from .. import constants
from ..schemas import api_schemas
from ..utils.exceptions import ServiceException
from ..utils.schema_extractor import get_schema_summary_from_db
from .chatbot_service import get_chatbot_with_validation, validate_chatbot_status, get_chatbot_db
from .helpers import extract_bigquery_info, clear_agent_cache

logger = logging.getLogger(__name__)


def create_template_with_bigquery_info(content: str, chatbot: dict, include_schema: bool = False) -> str:
    """Helper to assemble template content with context."""
    final_content = content
    if chatbot.get("db_type") == "bigquery":
        bigquery_info = extract_bigquery_info(
            chatbot.get("db_url"), chatbot.get("db_type"))
        if bigquery_info:
            header = f"BigQuery Configuration:\n- Project ID: {bigquery_info['project_id']}\n- Dataset ID: {bigquery_info['dataset_id']}\n\n"
            final_content = header + final_content

    if include_schema and chatbot.get("db_url"):
        try:
            summary = get_schema_summary_from_db(chatbot["db_url"], chatbot.get(
                "db_type", "sqlite"), chatbot.get("credentials_json"))
            final_content = f"Database Schema:\n{summary}\n\nTemplate Content:\n{final_content}"
        except Exception as e:
            raise ServiceException(f"Failed to include schema: {str(e)}", 500)
    return final_content


def configure_template_for_chatbot_service(chatbot_id: str):
    """Configures the template for a chatbot. Parses request internally."""
    try:
        data = api_schemas.TemplateConfigSchema().load(
            request.get_json(silent=True) or {})
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "llm_configured")

    db, template_id = get_chatbot_db(), data.get("template_id")
    name, description, content = data.get("name"), data.get(
        "description"), data.get("content")
    include_schema = data.get("include_schema", False)

    if template_id:
        template = get_template_by_id_service(template_id)
        db.update_chatbot(chatbot_id=chatbot_id,
                          template_id=template_id, status="template_configured")
        return {"message": "Template configured successfully", "chatbot_id": chatbot_id, "template": template}

    elif all([name, description, content]):
        final_content = create_template_with_bigquery_info(
            content, chatbot, include_schema)
        template = db.create_template(
            name=name, description=description, content=final_content, owner="admin", visibility="private")
        db.update_chatbot(
            chatbot_id=chatbot_id, template_id=template["id"], status="template_configured")
        return {"message": "Custom template created and configured", "chatbot_id": chatbot_id, "template": template}

    elif name is None and description is None and content is None:
        db.update_chatbot(chatbot_id=chatbot_id,
                          template_id=None, status="template_configured")
        return {"message": "Template configured to use default", "chatbot_id": chatbot_id}

    raise ServiceException(
        "Provide either 'template_id', all of 'name', 'description', and 'content', or none to use default.", 400)


def update_chatbot_template_service(chatbot_id: str):
    """Updates the template for a chatbot. Parses request internally."""
    try:
        data = api_schemas.TemplateUpdateSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "template_configured")

    final_content = create_template_with_bigquery_info(
        data['content'], chatbot, data.get('include_schema', False))
    db = get_chatbot_db()
    template_id = chatbot.get("template_id")

    if template_id:
        db.update_template(
            template_id, name=data['name'], description=data['description'], content=final_content)
    else:
        new_template = db.create_template(
            data['name'], data['description'], final_content)
        template_id = new_template["id"]
        db.update_chatbot(chatbot_id=chatbot_id, template_id=template_id)

    clear_agent_cache(chatbot_id)
    return {"message": "Template updated successfully", "chatbot_id": chatbot_id, "template_id": template_id}


def get_chatbot_template_service(chatbot_id: str):
    """Gets the template configured for a specific chatbot."""
    chatbot = get_chatbot_with_validation(chatbot_id)
    template_id = chatbot.get("template_id")
    if not template_id:
        raise ServiceException("No template configured for this chatbot", 404)
    return get_template_by_id_service(template_id)


def get_all_templates_service():
    """Gets all global templates. Parses request args internally."""
    db = get_chatbot_db()
    filters = {
        "owner": request.args.get("owner"), "visibility": request.args.get("visibility"),
        "search": request.args.get("search", "").strip(), "chatbot_id": request.args.get("chatbot_id")
    }
    templates = db.get_all_templates(
        **{k: v for k, v in filters.items() if k != 'search'})
    if search_term := filters.get("search"):
        search_lower = search_term.lower()
        templates = [t for t in templates if (search_lower in t.get("name", "").lower() or search_lower in t.get(
            "description", "").lower() or search_lower in (t.get("dataset_domain") or "").lower())]
    return templates


def get_template_by_id_service(template_id: int):
    """Gets a global template by its ID."""
    db = get_chatbot_db()
    template = db.get_template_by_id(template_id)
    if not template:
        raise ServiceException("Template not found", 404)
    return template


def create_global_template_service():
    """Creates a new global template. Parses request internally."""
    try:
        data = api_schemas.GlobalTemplateCreateSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)
    db = get_chatbot_db()
    return db.create_template(**data)


def update_global_template_service(template_id: int):
    """Updates a global template. Parses request internally."""
    try:
        data = api_schemas.GlobalTemplateUpdateSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)
    db = get_chatbot_db()
    get_template_by_id_service(template_id)
    updated_template = db.update_template(template_id, **data)
    if not updated_template:
        raise ServiceException("Failed to update template", 500)
    return updated_template


def delete_global_template_service(template_id: int):
    """Deletes a global template."""
    db = get_chatbot_db()
    get_template_by_id_service(template_id)
    conversations = db.get_conversations_by_template_id(template_id)
    active_conversations = [
        c for c in conversations if db.get_chatbot(c.get('chatbot_id'))]
    if active_conversations:
        raise ServiceException(
            f"Cannot delete template. Used by {len(active_conversations)} active conversation(s).", 400)

    db.delete_template(template_id)
    return {"message": "Template deleted successfully", "template_id": template_id}


def preview_template_service(template_id: int):
    """Generates a template preview. Parses request internally."""
    try:
        data = api_schemas.TemplatePreviewSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    template = get_template_by_id_service(template_id)
    chatbot_id, include_schema = data["chatbot_id"], data["include_schema"]

    final_prompt, schema_summary = template["content"], ""
    if include_schema:
        try:
            chatbot = get_chatbot_with_validation(chatbot_id)
            if chatbot.get("db_url"):
                summary = get_schema_summary_from_db(chatbot["db_url"], chatbot.get(
                    "db_type"), chatbot.get("credentials_json"))
                schema_summary = summary
                final_prompt = f"Database Schema:\n{summary}\n\nTemplate Content:\n{final_prompt}"
        except Exception as e:
            logger.warning(
                f"Could not generate schema for template preview: {e}")

    return {"template": template, "schema_summary": schema_summary, "final_prompt": final_prompt, "include_schema": include_schema}
