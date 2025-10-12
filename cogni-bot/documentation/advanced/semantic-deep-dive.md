# Semantic Model & Knowledge Flow (Deep Dive)

This page explains the data flow that powers CogniBot’s accuracy and efficiency: the semantic schema, the semantic knowledge cache, the Intent Picker, and the Context Clipper.

- For the Pydantic models, see [Semantic Schema Guide](../guides/schema.md).
- For agent wiring, see [Agents & Workflow](../guides/agents.md).

## 1) Semantic Schema (stored per chatbot)
- File: `app/schemas/semantic_models.py`
- Model: `DatabaseSchema` containing tables (`SemanticTable`), columns (`SemanticColumn`), relationships (`SemanticRelationship`), date aliases, and aliases.
- Storage: serialized JSON in `chatbots.semantic_schema_json` via `ChatbotDbUtil.store_semantic_schema()`.
- Creation path:
  1. Configure DB → `SchemaExtractor` extracts raw schema
  2. `convert_raw_schema_to_semantic()` converts into `DatabaseSchema`
  3. JSON is stored; knowledge cache is built
- Access APIs:
  - GET `/api/chatbots/{id}/semantic-schema`
  - PUT `/api/chatbots/{id}/semantic-schema`

## 2) Semantic Knowledge Cache
- Table: `semantic_knowledge_cache` (id, chatbot_id, chatbot_name, knowledge_data JSON)
- Builder: `knowledge_cache_service.build_and_store_knowledge_cache(chatbot_id)`
- Purpose: provide a compact, query-focused inventory of tables, columns, relationships, synonyms, and date aliases used by downstream agents.

## 3) Intent Picker
- File: `app/agents/intent_picker.py`
- Input: user question and knowledge cache
- Process:
  - Extracts simple keywords from the question
  - Scores tables/columns/synonyms and selects a minimal set
  - Produces intent JSON: `{tables, columns, filters, joins, order_by, date_range}`
  - Persists intent inline in the message stream as a `system`/`ai` message `INTENT:{...}`
- Output: updated state with `intent`

## 4) Context Clipper
- File: `app/agents/context_clipper.py`
- Input: state with `intent` and knowledge cache
- Process:
  - Normalizes target tables/columns from intent
  - Selects only relevant tables, a subset of relationships, and date aliases
  - Persists a `system` message `CLIPPED:{...}` with the clipped context
- Output: updated state with `clipped_context`

## 5) Prompt construction downstream
- Query Generator reads `INTENT:{...}` and `CLIPPED:{...}` from the message stream.
- Relationships included in prompts are hard-limited to bound token usage.
- DB-specific instructions are injected based on the current application DB type.

## 6) Benefits observed in code
- Smaller prompts with relevant objects only
- Tighter table constraints for SQL generation (disallows out-of-context tables)
- Reusable structured context across nodes (Validator, Rephraser)

## Related References
- [Schema Guide](../guides/schema.md)
- [Agents & Workflow](../guides/agents.md)
- [API Reference](../reference/api.md)
- [User Guide](../user-guide.md)
