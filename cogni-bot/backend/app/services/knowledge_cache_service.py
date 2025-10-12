import json
from typing import Any, Dict
from flask import current_app


def get_chatbot_db():
    return current_app.config['PROJECT_DB']


def build_schema_hashmap(semantic_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a flat key-value hashmap from the semantic schema for fast keyword lookups.
    Key format examples:
      - "schema:id" -> "..."
      - "schema:display_name" -> "..."
      - "table:<table>" -> { ...table metadata... }
      - "column:<table>.<column>" -> { ...column metadata... }
      - "synonym:table:<synonym>" -> ["<table>", ...]
      - "synonym:column:<synonym>" -> ["<table>.<column>", ...]
      - "metric:db:<metric_name>" -> { ...metric... }
      - "relationship:<index>" -> { ...relationship object... }
      - "date_alias:<alias>" -> { ...date alias config... }
    Values are JSON-serializable (no sets).
    """
    kv: Dict[str, Any] = {}

    # Basic database-level info
    kv["schema:id"] = semantic_schema.get("id")
    kv["schema:display_name"] = semantic_schema.get("display_name")
    kv["schema:dialect"] = semantic_schema.get("dialect")
    kv["schema:prefix"] = semantic_schema.get("schema_prefix")

    # Global aliases
    aliases = semantic_schema.get("aliases", {}) or {}
    kv["schema:aliases"] = aliases

    # Date aliases
    date_aliases = semantic_schema.get("date_aliases", {}) or {}
    for alias_name, alias_val in (date_aliases or {}).items():
        kv[f"date_alias:{alias_name}"] = alias_val

    # Tables, columns, metrics, relationships and synonyms
    tables = semantic_schema.get("tables", {}) or {}
    for table_name, table in tables.items():
        table_meta = {
            # Core
            "display_name": table.get("display_name", table_name),
            "description": table.get("description"),
            "business_context": table.get("business_context"),
            "row_count_estimate": table.get("row_count_estimate"),
            # Identity/lineage
            "database_id": table.get("database_id"),
            "schema_name": table.get("schema_name") or table.get("schema"),
            "table_id": table.get("table_id") or table.get("id"),
            # Timestamps/extra
            "created_at": table.get("created_at"),
            "updated_at": table.get("updated_at"),
            # Collections
            "synonyms": table.get("synonyms", []),
            # We will also expose metrics under metric:table:* keys below, but keep a copy here
            "metrics": table.get("metrics", {}),
            # Arbitrary metadata passthrough if present
            "metadata": table.get("metadata", {}),
        }
        kv[f"table:{table_name}"] = table_meta

        # Table synonyms -> tables list
        for syn in table_meta.get("synonyms", []) or []:
            syn_key = str(syn.get("synonym") if isinstance(syn, dict) else syn).lower()
            if syn_key:
                existing = kv.get(f"synonym:table:{syn_key}", [])
                if table_name not in existing:
                    existing.append(table_name)
                kv[f"synonym:table:{syn_key}"] = existing

        # Columns (carry over full, rich metadata so LLM has complete context)
        for col_name, col in (table.get("columns", {}) or {}).items():
            col_meta = {
                # Core semantics
                "display_name": col.get("display_name", col_name),
                "description": col.get("description"),
                # Types (support both legacy data_type and new type)
                "data_type": col.get("data_type") or col.get("type"),
                "type": col.get("type") or col.get("data_type"),
                # Keys/constraints
                "is_pk": bool(col.get("is_pk") or col.get("pk")),
                "pk": bool(col.get("pk") or col.get("is_pk")),
                "unique": bool(col.get("unique", False)),
                # Defaults
                "default": col.get("default"),
                # Foreign keys (preserve both boolean/object forms if present)
                "fk": col.get("fk"),
                "fk_ref": col.get("fk_ref") or (
                    {"table": (col.get("fk") or {}).get("table"), "column": (col.get("fk") or {}).get("column")} if isinstance(col.get("fk"), dict) else None
                ),
                # Synonyms and samples
                "synonyms": col.get("synonyms", []),
                # Misc passthrough
                "metadata": col.get("metadata", {}),
                "created_at": col.get("created_at"),
                "updated_at": col.get("updated_at"),
            }
            kv[f"column:{table_name}.{col_name}"] = col_meta

            # Column synonyms -> ["table.col", ...]
            for syn in col_meta.get("synonyms", []) or []:
                syn_key = str(syn.get("synonym") if isinstance(syn, dict) else syn).lower()
                if syn_key:
                    ref = f"{table_name}.{col_name}"
                    existing = kv.get(f"synonym:column:{syn_key}", [])
                    if ref not in existing:
                        existing.append(ref)
                    kv[f"synonym:column:{syn_key}"] = existing

    # Relationships (store with all available fields)
    for idx, rel in enumerate(semantic_schema.get("relationships", []) or []):
        kv[f"relationship:{idx}"] = rel

    # Table-level metrics: expose each explicitly for discovery in prompts
    for table_name, table in tables.items():
        for mname, metric in (table.get("metrics", {}) or {}).items():
            kv[f"metric:table:{table_name}.{str(mname).lower()}"] = metric

    # Database-level metrics
    metrics = semantic_schema.get("metrics", []) or []
    for m in metrics:
        if isinstance(m, dict):
            mname = m.get("name") or m.get("metric") or m.get("id")
            if mname:
                kv[f"metric:db:{str(mname).lower()}"] = m
        else:
            kv[f"metric:db:{str(m).lower()}"] = {"name": str(m), "expression": "COUNT(*)", "default_filters": []}

    return kv


def build_and_store_knowledge_cache(chatbot_id: str) -> Dict[str, Any]:
    """
    Loads semantic_schema_json for a chatbot, converts it into a flattened hashmap,
    and stores it in semantic_knowledge_cache. Returns the stored row.
    """
    db = get_chatbot_db()

    semantic_schema_json = db.get_semantic_schema(chatbot_id)
    if not semantic_schema_json:
        raise ValueError("No semantic schema found for this chatbot")

    semantic_schema = json.loads(semantic_schema_json)
    hashmap = build_schema_hashmap(semantic_schema)

    chatbot = db.get_chatbot(chatbot_id)
    # get_chatbot returns key 'chatbot_name' (labeled select). Fallback to 'name' just in case.
    chatbot_name = None
    if chatbot:
        chatbot_name = chatbot.get("chatbot_name") or chatbot.get("name")

    stored = db.upsert_semantic_knowledge_cache(
        chatbot_id=chatbot_id,
        chatbot_name=chatbot_name,
        knowledge_data=hashmap,
    )
    return stored


