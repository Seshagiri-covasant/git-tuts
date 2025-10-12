# Data Models

## Chatbot
- chatbot_id, name, db_type, db_url, current_llm_name, temperature, status, template_id, efficiency, credentials_json, semantic_schema_json, created_at

## Conversation
- conversation_id, chatbot_id, conversation_name, conversation_type, template_id, start_time, end_time, status, owner

## Interaction
- interaction_id, conversation_id, request, final_result, cleaned_query, timestamps, is_system_message, rating

## Template
- id, name, description, content, owner, visibility, shared_with, dataset_domain, created_at, updated_at

## Knowledge Cache
- id, chatbot_id, chatbot_name, knowledge_data (JSON)

## Semantic Schema (Pydantic)
- `DatabaseSchema`, `SemanticTable`, `SemanticColumn`, `SemanticRelationship`, `BusinessMetric`, `DateAlias`, `TableAliases`, `ConnectionConfig`
- See `guides/schema.md` for structure and lifecycle
