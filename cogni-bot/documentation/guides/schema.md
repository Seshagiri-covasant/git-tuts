# Semantic Schema

CogniBot stores a semantic schema per chatbot as JSON in the `chatbots` table (`semantic_schema_json`).

## Model
- Root model `DatabaseSchema` (Pydantic) in `app/schemas/semantic_models.py` with:
  - `tables: Dict[str, SemanticTable]`
  - `relationships: List[SemanticRelationship]`
  - `date_aliases: Dict[str, DateAlias]`
  - `aliases` for table/column aliases
  - `metrics` at DB-level and per-table

## Lifecycle
1. Configure DB → `SchemaExtractor` extracts raw schema
2. Convert to semantic model with `convert_raw_schema_to_semantic`
3. Store JSON via `ChatbotDbUtil.store_semantic_schema`
4. Knowledge cache built (`knowledge_cache_service.build_and_store_knowledge_cache`)

## Access
- GET `/api/chatbots/{id}/semantic-schema` returns normalized JSON
- PUT `/api/chatbots/{id}/semantic-schema` validates, stores, and rebuilds knowledge cache

## Backward compatibility
- Services normalize legacy forms (e.g., metrics arrays, FK booleans) before validation.
