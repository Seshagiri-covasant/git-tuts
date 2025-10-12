import json
import re
from typing import Any, Dict, List, Set


class IntentPickerAgent:
    def __init__(self, llm):
        self.llm = llm

    def _build_knowledge_overview(self, knowledge_data: Dict[str, Any], question: str) -> str:
        """Build a compact, question-focused overview to minimize tokens and speed up LLM.

        Strategy:
        - Extract simple keywords from the question
        - Prefer tables/columns whose names contain these keywords
        - Hard-limit totals to keep prompt small
        """
        # Extract lowercase keywords (alnum 3+ chars)
        keywords: Set[str] = set(re.findall(r"[a-zA-Z0-9_]{3,}", (question or "").lower()))

        # Buckets
        tables_all: List[str] = []
        columns_all: List[str] = []
        synonyms_table_all: List[str] = []
        synonyms_column_all: List[str] = []

        for k, v in (knowledge_data or {}).items():
            if k.startswith("table:"):
                tables_all.append(k.split(":", 1)[1])
            elif k.startswith("column:"):
                columns_all.append(k.split(":", 1)[1])
            elif k.startswith("synonym:table:") and isinstance(v, list):
                synonyms_table_all.append(f"{k.replace('synonym:table:','')} -> {', '.join(v)}")
            elif k.startswith("synonym:column:") and isinstance(v, list):
                synonyms_column_all.append(f"{k.replace('synonym:column:','')} -> {', '.join(v)}")

        def score(name: str) -> int:
            n = name.lower()
            return sum(1 for kw in keywords if kw in n)

        # Sort by relevance score, fallback to name
        tables_sorted = sorted(tables_all, key=lambda n: (-score(n), n))
        columns_sorted = sorted(columns_all, key=lambda n: (-score(n), n))
        syn_t_sorted = sorted(synonyms_table_all, key=lambda n: (-score(n.split(' -> ',1)[0]), n))
        syn_c_sorted = sorted(synonyms_column_all, key=lambda n: (-score(n.split(' -> ',1)[0]), n))

        # Hard limits to keep prompt tight
        MAX_TABLES = 40
        MAX_COLUMNS = 200
        MAX_SYN = 60

        overview = "\n".join([
            "TABLES:", ", ".join(tables_sorted[:MAX_TABLES]) or "",
            "\nCOLUMNS:", ", ".join(columns_sorted[:MAX_COLUMNS]) or "",
            "\nTABLE SYNONYMS:", "\n".join(syn_t_sorted[:MAX_SYN]) or "",
            "\nCOLUMN SYNONYMS:", "\n".join(syn_c_sorted[:MAX_SYN]) or "",
        ])
        return overview

    def run(self, state: dict, chatbot_id: str, chatbot_db_util) -> dict:
        # Extract question
        last_msg = state["messages"][-1]
        question = last_msg["content"] if isinstance(last_msg, dict) and "content" in last_msg else str(last_msg)

        # Load knowledge cache
        cache = None
        knowledge_data: Dict[str, Any] = {}
        schema: Dict[str, Any] | None = None
        try:
            cache = chatbot_db_util.get_semantic_knowledge_cache(chatbot_id)
            knowledge_data = cache.get("knowledge_data") if cache else {}
        except Exception:
            knowledge_data = {}

        # If cache is empty or missing, try to build a minimal overview directly
        # from the stored semantic schema so intent picking still works.
        if not knowledge_data:
            try:
                schema_json_str = chatbot_db_util.get_semantic_schema(chatbot_id)
                if schema_json_str:
                    schema = json.loads(schema_json_str)
                    # Build a lightweight hashmap inline (subset of knowledge_cache_service)
                    temp_kv: Dict[str, Any] = {}
                    tables = (schema or {}).get("tables", {}) or {}
                    for table_name, table in tables.items():
                        temp_kv[f"table:{table_name}"] = table_name
                        for col in (table or {}).get("columns", []) or []:
                            col_name = col.get("name") if isinstance(col, dict) else None
                            if col_name:
                                temp_kv[f"column:{table_name}.{col_name}"] = f"{table_name}.{col_name}"
                    # synonyms (optional)
                    synonyms = (schema or {}).get("aliases", {}) or {}
                    for syn, targets in (synonyms or {}).items():
                        if isinstance(targets, list):
                            temp_kv[f"synonym:table:{syn}"] = [str(t) for t in targets]
                    knowledge_data = temp_kv
            except Exception:
                # Best-effort; continue with empty knowledge
                knowledge_data = {}

        # If schema not set yet (because cache existed), still try loading it for metrics
        if not schema:
            try:
                schema_json_str = chatbot_db_util.get_semantic_schema(chatbot_id)
                if schema_json_str:
                    schema = json.loads(schema_json_str)
            except Exception:
                schema = None

        # Build compact overview for LLM (question-focused clipping)
        overview = self._build_knowledge_overview(knowledge_data, question)

        # Append GLOBAL and TABLE METRICS if available from schema
        metrics_blocks: List[str] = []
        try:
            if schema:
                # Global metrics
                gm = (schema or {}).get("metrics") or []
                global_metrics_list: List[str] = []
                if isinstance(gm, list):
                    for m in gm:
                        if isinstance(m, dict):
                            name = m.get("name") or m.get("metric") or None
                            expr = m.get("expression") or m.get("value") or None
                            if name:
                                global_metrics_list.append(f"{name}{f' = {expr}' if expr else ''}")
                elif isinstance(gm, dict):
                    for name, m in gm.items():
                        if isinstance(m, dict):
                            expr = m.get("expression") or m.get("value") or None
                            global_metrics_list.append(f"{name}{f' = {expr}' if expr else ''}")
                        else:
                            global_metrics_list.append(str(name))
                if global_metrics_list:
                    metrics_blocks.append("GLOBAL METRICS:\n" + ", ".join(global_metrics_list))

                # Table metrics (summarized per table)
                tables = (schema or {}).get("tables", {}) or {}
                table_metrics_lines: List[str] = []
                for t_name, t in tables.items():
                    tm = (t or {}).get("metrics") or {}
                    names: List[str] = []
                    if isinstance(tm, dict):
                        names = list(tm.keys())
                    elif isinstance(tm, list):
                        for m in tm:
                            if isinstance(m, dict) and m.get("name"):
                                names.append(str(m.get("name")))
                            elif isinstance(m, str):
                                names.append(m)
                    if names:
                        table_metrics_lines.append(f"{t_name}: {', '.join(sorted(names))}")
                if table_metrics_lines:
                    metrics_blocks.append("TABLE METRICS:\n" + "\n".join(table_metrics_lines[:100]))
        except Exception:
            pass

        metrics_text = ("\n\n" + "\n\n".join(metrics_blocks)) if metrics_blocks else ""

        prompt = f"""
You are an intent picker for SQL generation.
Given a user question and a database knowledge overview (tables, columns, synonyms, global metrics, table metrics),
identify the minimal set of required tables and specific columns, plus likely filters, joins, order_by, and date_range.

Return STRICT JSON with keys: tables, columns, filters, joins, order_by, date_range.
If a synonym is used in the question, map it to actual table/column using the overview.

QUESTION:
{question}

KNOWLEDGE OVERVIEW:
{overview}
{metrics_text}

JSON ONLY:
"""

        try:
            print(f"[Intent_Picker] Prompt to LLM (chatbot {chatbot_id}):\n{prompt}")
        except Exception:
            pass

        response = self.llm.invoke(prompt)

        # Normalize varied LLM outputs into a JSON string
        raw_content = getattr(response, "content", None)

        # Some providers return list content; extract text parts
        if isinstance(raw_content, list):
            try:
                joined = "\n".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in raw_content
                )
                raw_text = joined
            except Exception:
                raw_text = str(raw_content)
        else:
            raw_text = str(raw_content) if raw_content is not None else str(response)

        # Try direct JSON parse first
        intent: Dict[str, Any] | None = None
        try:
            intent = json.loads(raw_text)
        except Exception:
            # Try to extract JSON object from code fences or surrounding text
            try:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE)
                if match:
                    intent = json.loads(match.group(1))
                else:
                    match2 = re.search(r"\{[\s\S]*\}", raw_text)
                    if match2:
                        intent = json.loads(match2.group(0))
            except Exception:
                intent = None

        if not isinstance(intent, dict):
            # Fallback minimal intent
            intent = {
                "tables": [],
                "columns": [],
                "filters": [],
                "joins": [],
                "order_by": [],
                "date_range": None
            }

        state = dict(state)
        state["intent"] = intent
        # Persist intent in MessagesState by adding a system message
        try:
            state_messages = list(state.get("messages", []))
            payload = json.dumps(intent)
            # Append as both system and ai for robustness across message role handling
            state_messages.append({"role": "system", "content": f"INTENT:{payload}"})
            state_messages.append({"role": "ai", "content": f"INTENT:{payload}"})
            state["messages"] = state_messages
        except Exception:
            pass
        try:
            print(f"[Intent_Picker] Intent for chatbot {chatbot_id}: {json.dumps(intent)[:1000]}")
            print(f"[Intent_Picker] Intent tables type={type(intent.get('tables'))} value={intent.get('tables')}")
            print(f"[Intent_Picker] Intent columns type={type(intent.get('columns'))} value={intent.get('columns')}")
        except Exception:
            pass
        return state


