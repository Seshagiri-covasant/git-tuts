from typing import Any, Dict


class ContextClipperAgent:
    def __init__(self):
        pass

    def run(self, state: dict, chatbot_id: str, chatbot_db_util) -> dict:
        # Get intent from state (direct) or from last system message fallback
        intent = {}
        # Always recover intent from messages because MessagesState may drop ad-hoc keys
        for msg in reversed(state.get("messages", [])):
            content_str = None
            if isinstance(msg, dict):
                c = msg.get("content")
                if isinstance(c, str):
                    content_str = c
            elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                content_str = getattr(msg, "content")
            if content_str and content_str.startswith("INTENT:"):
                import json as _json
                try:
                    intent = _json.loads(content_str[7:])
                except Exception:
                    intent = {}
                break

        # Normalize targets
        raw_tables = intent.get("tables") or []
        raw_columns = intent.get("columns") or []
        # Normalize to strings
        raw_tables = [str(t) for t in raw_tables if t is not None]
        raw_columns = [str(c) for c in raw_columns if c is not None]
        # Derive tables from qualified columns if tables list is empty
        derived_tables = []
        for colref in raw_columns:
            if isinstance(colref, str) and "." in colref:
                derived_tables.append(colref.split(".", 1)[0])
        # Also include raw_tables directly from intent
        target_tables = set(raw_tables or derived_tables)
        target_columns = set(raw_columns)

        # Expand with tables mentioned in joins in intent
        for j in intent.get("joins") or []:
            try:
                ta = j.get("table_a")
                tb = j.get("table_b")
                if ta:
                    target_tables.add(ta)
                if tb:
                    target_tables.add(tb)
            except Exception:
                pass

        cache = chatbot_db_util.get_semantic_knowledge_cache(chatbot_id)
        knowledge = cache.get("knowledge_data") if cache else {}

        clipped: Dict[str, Any] = {
            "tables": {},
            "relationships": [],
            "metrics": [],
            "date_aliases": {},
        }

        # Tables (strict match to target if provided)
        for key, meta in knowledge.items():
            if key.startswith("table:"):
                tname = key.split(":", 1)[1]
                if not target_tables or tname in target_tables:
                    clipped["tables"][tname] = {
                        "display_name": meta.get("display_name"),
                        "metrics": meta.get("metrics", {}),
                        "columns": {}
                    }

        # Columns (exact or table.* match); if target_columns empty, include all for selected tables
        for key, meta in knowledge.items():
            if key.startswith("column:"):
                ref = key.split(":", 1)[1]
                tname, cname = ref.split(".", 1)
                include_col = False
                if not target_tables or tname in target_tables:
                    if not target_columns:
                        include_col = True
                    else:
                        include_col = (
                            ref in target_columns or
                            cname in target_columns or
                            f"{tname}.*" in target_columns
                        )
                if include_col:
                    if tname in clipped["tables"]:
                        clipped["tables"][tname]["columns"][cname] = {
                            "display_name": meta.get("display_name"),
                            "data_type": meta.get("data_type"),
                            "is_pk": meta.get("is_pk"),
                            "fk": meta.get("fk"),
                            "description": meta.get("description"),
                        }

        # Relationships - only include those involving target tables
        for key, rel in knowledge.items():
            if key.startswith("relationship:"):
                # Check if the relationship involves any of our target tables
                from_table = rel.get("from", "").split(".")[0] if "." in rel.get("from", "") else ""
                to_table = rel.get("to", "").split(".")[0] if "." in rel.get("to", "") else ""
                
                # Include relationship if either table is in our target tables
                if target_tables and (from_table in target_tables or to_table in target_tables):
                    clipped["relationships"].append(rel)

        # Date aliases
        for key, val in knowledge.items():
            if key.startswith("date_alias:"):
                aname = key.split(":", 1)[1]
                clipped["date_aliases"][aname] = val

        # DB level metrics
        for key, m in knowledge.items():
            if key.startswith("metric:db:"):
                clipped["metrics"].append(m)

        state = dict(state)
        state["clipped_context"] = clipped
        # Persist clipped context in MessagesState by adding a system message
        try:
            import json as _json
            msgs = list(state.get("messages", []))
            msgs.append({"role": "system", "content": f"CLIPPED:{_json.dumps(clipped)}"})
            state["messages"] = msgs
        except Exception:
            pass
        try:
            import json as _json
            print(f"[Context_Clipper] Targets tables={list(target_tables)} columns={list(target_columns)}")
            print(f"[Context_Clipper] Clipped context for chatbot {chatbot_id}: {_json.dumps(clipped)[:1000]}")
        except Exception:
            pass
        return state


