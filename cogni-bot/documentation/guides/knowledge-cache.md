# Knowledge Cache

The semantic knowledge cache accelerates and constrains reasoning by providing a compact, searchable inventory of tables, columns, synonyms, relationships, and date aliases.

- Table: `semantic_knowledge_cache`
- Keys: `chatbot_id`, `knowledge_data` (JSON)

## Build
- Built after schema extraction and on semantic schema updates: `knowledge_cache_service.build_and_store_knowledge_cache(chatbot_id)`

## Use
- Intent Picker: filters and scores items based on keywords from the user question
- Context Clipper: selects only needed tables/columns and relationships for prompts

## Maintenance
- Clear and rebuild via schema update
- Size is bounded by clipping in agents; overview hard-limits keep prompts small
