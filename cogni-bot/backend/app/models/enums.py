from enum import Enum


class ChatbotStatus(Enum):
    CREATED = "created"
    DB_CONFIGURED = "db_configured"
    LLM_CONFIGURED = "llm_configured"
    TEMPLATE_CONFIGURED = "template_configured"
    READY = "ready"
