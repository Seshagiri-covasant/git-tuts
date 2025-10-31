from marshmallow import Schema, fields, validate
from .. import constants

# --- Chatbot Schemas ---


class ChatbotCreateSchema(Schema):
    name = fields.String(
        required=True, description="The name for the new chatbot.")
    temperature = fields.Float(
        required=False, missing=0.7, validate=validate.Range(min=0.0, max=1.0))


class DBConfigSchema(Schema):
    db_type = fields.String(
        required=True, validate=validate.OneOf(constants.DB_TYPES))
    db_name = fields.String(required=True)
    schema_name = fields.String(required=False, allow_none=True)
    selected_tables = fields.List(fields.String(), required=False, missing=[])

    # Fields for PostgreSQL
    username = fields.String()
    password = fields.String()
    host = fields.String()
    port = fields.Raw()
    # Optional MSSQL driver
    driver = fields.String()

    # Fields for BigQuery
    project_id = fields.String()
    dataset_id = fields.String()
    credentials_json = fields.String()


class LLMConfigSchema(Schema):
    llm_name = fields.String(
        required=True, validate=validate.OneOf(constants.LLM_NAMES))
    temperature = fields.Float(
        required=False, validate=validate.Range(min=0.0, max=1.0))


class ReadySchema(Schema):
    preview_content = fields.String(
        required=False, description="Content to help generate the enhanced prompt.")


class KnowledgeBaseSchema(Schema):
    industry = fields.String(required=True)
    vertical = fields.String(required=True)
    domain = fields.String(required=True)
    knowledge_base_file = fields.String(required=False)

# --- Conversation Schemas ---


class ConversationCreateSchema(Schema):
    conversation_name = fields.String(required=True)
    owner = fields.String(required=True)


class InteractionCreateSchema(Schema):
    request = fields.String(required=True)
    llm_name = fields.String(required=False)


class InteractionRatingSchema(Schema):
    rating = fields.Integer(required=True, validate=validate.OneOf([1, -1]))


class HumanApprovalSchema(Schema):
    human_response = fields.Dict(required=True, description="Human response to approval request")
    approval_type = fields.String(required=False, missing="approval", validate=validate.OneOf(["approval", "clarification", "modification"]))

# --- Template Schemas ---


class TemplateConfigSchema(Schema):
    template_id = fields.Int(required=False)
    name = fields.String(required=False)
    description = fields.String(required=False)
    content = fields.String(required=False)
    include_schema = fields.Boolean(missing=False)
    dataset_domain = fields.String(required=False, allow_none=True)


class TemplateUpdateSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(required=True)
    content = fields.String(required=True)
    include_schema = fields.Boolean(missing=False)
    dataset_domain = fields.String(required=False, allow_none=True)


class GlobalTemplateCreateSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(required=True)
    content = fields.String(required=True)
    owner = fields.String(missing="admin")
    visibility = fields.String(missing="private", validate=validate.OneOf([
                               "public", "private", "shared"]))
    shared_with = fields.List(fields.String(), missing=[])
    dataset_domain = fields.String(required=False, allow_none=True)


class GlobalTemplateUpdateSchema(Schema):
    name = fields.String()
    description = fields.String()
    content = fields.String()
    owner = fields.String()
    visibility = fields.String(
        validate=validate.OneOf(["public", "private", "shared"]))
    shared_with = fields.List(fields.String())
    dataset_domain = fields.String(allow_none=True)


class TemplatePreviewSchema(Schema):
    chatbot_id = fields.String(required=True)
    include_schema = fields.Boolean(missing=False)

# --- LLM Service Schemas ---


class BAInsightSchema(Schema):
    table = fields.List(fields.Dict(), required=True)
    prompt = fields.String(missing="")
    llm_name = fields.String(required=False, allow_none=True)
    chatbot_id = fields.String(required=False)
    # Optional fields for caching and regeneration
    interaction_id = fields.String(required=False, allow_none=True)
    regenerate = fields.Boolean(missing=False)

class VisualizationSchema(Schema):
    table = fields.List(fields.Dict(), required=True)
    prompt = fields.String(missing="")
    sql_query = fields.String(missing="")
    llm_name = fields.String(required=False, allow_none=True)
    chatbot_id = fields.String(required=False)

# --- Benchmark Schemas ---


class BenchmarkRunSchema(Schema):
    temperature = fields.Float(
        required=False, validate=validate.Range(min=0.0, max=1.0))
    force = fields.Boolean(missing=False)


class CustomTestCreateSchema(Schema):
    test_name = fields.String(required=True)
    original_sql = fields.String(required=True)
    natural_question = fields.String(required=True)


class CustomTestRunSchema(Schema):
    test_name = fields.String(required=False, allow_none=True)
    temperature = fields.Float(
        required=False, validate=validate.Range(min=0.0, max=1.0))


class ConnectionTestSchema(Schema):
    db_type = fields.String(required=True, validate=validate.OneOf(
        ["sqlite", "postgresql", "bigquery", "mysql", "mssql"]))
    db_name = fields.String(required=True)
    schema_name = fields.String(required=False, allow_none=True)

    # Optional fields for PostgreSQL
    username = fields.String()
    password = fields.String()
    host = fields.String()
    port = fields.Raw()  # Accepts string or number
    # Optional MSSQL driver
    driver = fields.String()

    # Optional fields for BigQuery
    project_id = fields.String()
    dataset_id = fields.String()
    credentials_json = fields.String()

# --- New schemas for registration and unified interaction ---
class ChatbotRegisterSchema(Schema):
    clientId = fields.String(required=True)
    projectId = fields.String(required=True)

class UnifiedInteractionSchema(Schema):
    chatbot_id = fields.String(required=False, allow_none=True)
    clientId = fields.String(required=False, allow_none=True)
    projectId = fields.String(required=False, allow_none=True)
    message = fields.String(required=True)
    conversation_id = fields.String(required=False, allow_none=True)


class FollowUpQuestionSchema(Schema):
    question_id = fields.String(required=True, description="Unique identifier for the follow-up question")
    question = fields.String(required=True, description="The follow-up question text")
    answer_options = fields.List(fields.String(), required=True, description="List of possible answers for the follow-up question")
    multiple_selection = fields.Boolean(required=False, missing=False, description="Indicates if multiple answers can be selected")
    answers = fields.List(fields.String(), required=False, allow_none=True, description="The answers selected by the user")

class FollowUpResponseSchema(Schema):
    follow_up_questions = fields.List(fields.Nested(FollowUpQuestionSchema), required=False, allow_none=True)
    interaction_type = fields.String(required=True, description="Type of interaction: 'follow_up', 'clarification', 'human_approval', or 'final_result'")
    message = fields.String(required=False, description="Additional message to display to user")

