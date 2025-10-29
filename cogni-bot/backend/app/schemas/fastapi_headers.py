from fastapi import Header, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid

# --- FastAPI Header Models ---

class SQLAgentHeaders(BaseModel):
    """Headers for SQL Agent requests"""
    x_conversation_id: str = Header(..., alias="X-Conversation-ID")
    x_chatbot_id: str = Header(..., alias="X-Chatbot-ID")
    x_llm_name: Optional[str] = Header(None, alias="X-LLM-Name")
    x_temperature: Optional[float] = Header(0.7, alias="X-Temperature", ge=0.0, le=1.0)
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
    x_conversation_thread: Optional[str] = Header(None, alias="X-Conversation-Thread")
    x_original_question: Optional[str] = Header(None, alias="X-Original-Question")
    
    @validator('x_request_id', pre=True, always=True)
    def generate_request_id(cls, v):
        return v or str(uuid.uuid4())
    
    @validator('x_conversation_thread', pre=True, always=True)
    def generate_thread_id(cls, v):
        return v or str(uuid.uuid4())

class HumanApprovalHeaders(BaseModel):
    """Headers for Human Approval requests"""
    x_conversation_id: str = Header(..., alias="X-Conversation-ID")
    x_approval_type: str = Header(..., alias="X-Approval-Type")
    x_conversation_thread: str = Header(..., alias="X-Conversation-Thread")
    x_original_question: str = Header(..., alias="X-Original-Question")
    x_similar_columns: Optional[str] = Header(None, alias="X-Similar-Columns")
    x_ambiguity_analysis: Optional[str] = Header(None, alias="X-Ambiguity-Analysis")

class DatabaseConfigHeaders(BaseModel):
    """Headers for Database Configuration"""
    x_db_type: str = Header(..., alias="X-DB-Type")
    x_schema_name: Optional[str] = Header(None, alias="X-Schema-Name")
    x_host: Optional[str] = Header(None, alias="X-Host")
    x_port: Optional[int] = Header(None, alias="X-Port")
    x_driver: Optional[str] = Header(None, alias="X-Driver")
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID")
    x_dataset_id: Optional[str] = Header(None, alias="X-Dataset-ID")

class QueryGeneratorHeaders(BaseModel):
    """Headers for Query Generator"""
    x_query_type: Optional[str] = Header("select", alias="X-Query-Type")
    x_table_list: Optional[str] = Header(None, alias="X-Table-List")
    x_schema_context: Optional[str] = Header(None, alias="X-Schema-Context")
    x_ai_preferences: Optional[str] = Header(None, alias="X-AI-Preferences")
    x_aggregation_patterns: Optional[str] = Header(None, alias="X-Aggregation-Patterns")

class PerformanceHeaders(BaseModel):
    """Headers for Performance and Caching"""
    x_cache_control: Optional[str] = Header(None, alias="X-Cache-Control")
    x_etag: Optional[str] = Header(None, alias="X-ETag")
    x_rate_limit: Optional[int] = Header(None, alias="X-Rate-Limit")
    x_rate_limit_remaining: Optional[int] = Header(None, alias="X-Rate-Limit-Remaining")

class ErrorHeaders(BaseModel):
    """Headers for Error Responses"""
    x_error_code: Optional[str] = Header(None, alias="X-Error-Code")
    x_error_message: Optional[str] = Header(None, alias="X-Error-Message")
    x_retry_after: Optional[int] = Header(None, alias="X-Retry-After")

# --- Combined Header Models ---

class SQLAgentRequestHeaders(SQLAgentHeaders, QueryGeneratorHeaders, PerformanceHeaders):
    """Combined headers for SQL Agent requests"""
    pass

class HumanApprovalRequestHeaders(HumanApprovalHeaders, PerformanceHeaders):
    """Combined headers for Human Approval requests"""
    pass

class DatabaseConfigRequestHeaders(DatabaseConfigHeaders, PerformanceHeaders):
    """Combined headers for Database Configuration requests"""
    pass

# --- FastAPI Dependency Functions ---

def get_sql_agent_headers(
    x_conversation_id: str = Header(..., alias="X-Conversation-ID"),
    x_chatbot_id: str = Header(..., alias="X-Chatbot-ID"),
    x_llm_name: Optional[str] = Header(None, alias="X-LLM-Name"),
    x_temperature: Optional[float] = Header(0.7, alias="X-Temperature"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    x_conversation_thread: Optional[str] = Header(None, alias="X-Conversation-Thread"),
    x_original_question: Optional[str] = Header(None, alias="X-Original-Question"),
    x_query_type: Optional[str] = Header("select", alias="X-Query-Type"),
    x_table_list: Optional[str] = Header(None, alias="X-Table-List"),
    x_schema_context: Optional[str] = Header(None, alias="X-Schema-Context"),
    x_ai_preferences: Optional[str] = Header(None, alias="X-AI-Preferences"),
    x_aggregation_patterns: Optional[str] = Header(None, alias="X-Aggregation-Patterns"),
    x_cache_control: Optional[str] = Header(None, alias="X-Cache-Control"),
    x_etag: Optional[str] = Header(None, alias="X-ETag"),
    x_rate_limit: Optional[int] = Header(None, alias="X-Rate-Limit"),
    x_rate_limit_remaining: Optional[int] = Header(None, alias="X-Rate-Limit-Remaining")
) -> SQLAgentRequestHeaders:
    """Dependency function for SQL Agent headers"""
    return SQLAgentRequestHeaders(
        x_conversation_id=x_conversation_id,
        x_chatbot_id=x_chatbot_id,
        x_llm_name=x_llm_name,
        x_temperature=x_temperature,
        x_request_id=x_request_id or str(uuid.uuid4()),
        x_conversation_thread=x_conversation_thread or str(uuid.uuid4()),
        x_original_question=x_original_question,
        x_query_type=x_query_type,
        x_table_list=x_table_list,
        x_schema_context=x_schema_context,
        x_ai_preferences=x_ai_preferences,
        x_aggregation_patterns=x_aggregation_patterns,
        x_cache_control=x_cache_control,
        x_etag=x_etag,
        x_rate_limit=x_rate_limit,
        x_rate_limit_remaining=x_rate_limit_remaining
    )

def get_human_approval_headers(
    x_conversation_id: str = Header(..., alias="X-Conversation-ID"),
    x_approval_type: str = Header(..., alias="X-Approval-Type"),
    x_conversation_thread: str = Header(..., alias="X-Conversation-Thread"),
    x_original_question: str = Header(..., alias="X-Original-Question"),
    x_similar_columns: Optional[str] = Header(None, alias="X-Similar-Columns"),
    x_ambiguity_analysis: Optional[str] = Header(None, alias="X-Ambiguity-Analysis"),
    x_cache_control: Optional[str] = Header(None, alias="X-Cache-Control"),
    x_etag: Optional[str] = Header(None, alias="X-ETag"),
    x_rate_limit: Optional[int] = Header(None, alias="X-Rate-Limit"),
    x_rate_limit_remaining: Optional[int] = Header(None, alias="X-Rate-Limit-Remaining")
) -> HumanApprovalRequestHeaders:
    """Dependency function for Human Approval headers"""
    return HumanApprovalRequestHeaders(
        x_conversation_id=x_conversation_id,
        x_approval_type=x_approval_type,
        x_conversation_thread=x_conversation_thread,
        x_original_question=x_original_question,
        x_similar_columns=x_similar_columns,
        x_ambiguity_analysis=x_ambiguity_analysis,
        x_cache_control=x_cache_control,
        x_etag=x_etag,
        x_rate_limit=x_rate_limit,
        x_rate_limit_remaining=x_rate_limit_remaining
    )

def get_database_config_headers(
    x_db_type: str = Header(..., alias="X-DB-Type"),
    x_schema_name: Optional[str] = Header(None, alias="X-Schema-Name"),
    x_host: Optional[str] = Header(None, alias="X-Host"),
    x_port: Optional[int] = Header(None, alias="X-Port"),
    x_driver: Optional[str] = Header(None, alias="X-Driver"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID"),
    x_dataset_id: Optional[str] = Header(None, alias="X-Dataset-ID"),
    x_cache_control: Optional[str] = Header(None, alias="X-Cache-Control"),
    x_etag: Optional[str] = Header(None, alias="X-ETag"),
    x_rate_limit: Optional[int] = Header(None, alias="X-Rate-Limit"),
    x_rate_limit_remaining: Optional[int] = Header(None, alias="X-Rate-Limit-Remaining")
) -> DatabaseConfigRequestHeaders:
    """Dependency function for Database Configuration headers"""
    return DatabaseConfigRequestHeaders(
        x_db_type=x_db_type,
        x_schema_name=x_schema_name,
        x_host=x_host,
        x_port=x_port,
        x_driver=x_driver,
        x_project_id=x_project_id,
        x_dataset_id=x_dataset_id,
        x_cache_control=x_cache_control,
        x_etag=x_etag,
        x_rate_limit=x_rate_limit,
        x_rate_limit_remaining=x_rate_limit_remaining
    )

# --- Response Header Models ---

class SQLAgentResponseHeaders(BaseModel):
    """Response headers for SQL Agent"""
    x_interaction_id: str = Field(..., alias="X-Interaction-ID")
    x_conversation_thread: str = Field(..., alias="X-Conversation-Thread")
    x_processing_status: str = Field(..., alias="X-Processing-Status")
    x_sql_generated: bool = Field(..., alias="X-SQL-Generated")
    x_human_approval_required: bool = Field(..., alias="X-Human-Approval-Required")
    x_response_time: int = Field(..., alias="X-Response-Time")
    x_request_id: str = Field(..., alias="X-Request-ID")

class HumanApprovalResponseHeaders(BaseModel):
    """Response headers for Human Approval"""
    x_approval_processed: bool = Field(..., alias="X-Approval-Processed")
    x_conversation_thread: str = Field(..., alias="X-Conversation-Thread")
    x_original_question: str = Field(..., alias="X-Original-Question")
    x_response_time: int = Field(..., alias="X-Response-Time")
    x_request_id: str = Field(..., alias="X-Request-ID")

# --- FastAPI Response Headers ---

def create_sql_agent_response_headers(
    interaction_id: str,
    conversation_thread: str,
    processing_status: str,
    sql_generated: bool,
    human_approval_required: bool,
    response_time: int,
    request_id: str
) -> Dict[str, str]:
    """Create response headers for SQL Agent"""
    return {
        "X-Interaction-ID": interaction_id,
        "X-Conversation-Thread": conversation_thread,
        "X-Processing-Status": processing_status,
        "X-SQL-Generated": str(sql_generated).lower(),
        "X-Human-Approval-Required": str(human_approval_required).lower(),
        "X-Response-Time": str(response_time),
        "X-Request-ID": request_id
    }

def create_human_approval_response_headers(
    approval_processed: bool,
    conversation_thread: str,
    original_question: str,
    response_time: int,
    request_id: str
) -> Dict[str, str]:
    """Create response headers for Human Approval"""
    return {
        "X-Approval-Processed": str(approval_processed).lower(),
        "X-Conversation-Thread": conversation_thread,
        "X-Original-Question": original_question,
        "X-Response-Time": str(response_time),
        "X-Request-ID": request_id
    }






