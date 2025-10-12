from ..utils.exceptions import QueryGenerationException
from sqlalchemy import inspect, text
from ..utils.prompt_loader import get_prompt
import logging


class QueryGeneratorAgent:
    def __init__(self, llm, app_db_util=None, prompt_template=None, chatbot_db_util=None, chatbot_id: str | None = None):
        self.llm = llm
        self.app_db_util = app_db_util  # For application DB (query execution)
        # For chatbot data (chat_bot.db)
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id
        if not prompt_template:
            raise ValueError(
                "No template provided. Please provide a template content.")
        self.prompt_template = prompt_template

    def _get_database_type(self):
        """Detect database type from the database URL."""
        if not self.app_db_util:
            return "sqlite"  # Default fallback

        db_url = str(self.app_db_util.db_engine.url)
        if 'bigquery://' in db_url:
            return "bigquery"
        elif 'postgresql' in db_url or 'postgres://' in db_url:
            return "postgresql"
        elif 'mysql' in db_url:
            return "mysql"
        elif 'mssql' in db_url:
            return "mssql"
        else:
            return "sqlite"

    def _get_actual_table_names(self):
        """Get actual table names from the database to prevent case sensitivity issues."""
        try:
            if not self.app_db_util:
                return []

            inspector = inspect(self.app_db_util.db_engine)
            table_names = inspector.get_table_names()
            return table_names
        except Exception as e:
            logging.info(f"Error getting table names: {e}")

            return []

    def _get_database_specific_instructions(self, db_type, clipped_context=None, question=None):
        """Get database-specific SQL generation instructions with unified parameter handling."""
        # Get actual table names
        actual_tables = self._get_actual_table_names()
        
        # Prepare common parameters
        import json as _json
        
        # Get schema context from clipped context if available
        schema_ctx = {}
        if clipped_context and isinstance(clipped_context, dict):
            schema_ctx = clipped_context.get("tables", {})
        
        # Prepare table list based on database type
        if db_type == "bigquery":
            table_list = ", ".join([f'`{table}`' for table in actual_tables]) if actual_tables else "No tables found"
        else:
            table_list = ", ".join([f'"{table}"' for table in actual_tables]) if actual_tables else "No tables found"
        
        # Parse project/dataset for BigQuery
        project = ""
        dataset = ""
        if db_type == "bigquery":
            try:
                url_str = str(self.app_db_util.db_engine.url) if self.app_db_util else ""
                if "bigquery://" in url_str:
                    remainder = url_str.split("bigquery://", 1)[1]
                    parts = remainder.split("/")
                    if len(parts) >= 2:
                        project = parts[0]
                        dataset = parts[1]
            except Exception:
                pass

        # Determine selected schema_name for dialects that support it (postgresql, mssql)
        selected_schema = None
        try:
            if self.chatbot_db_util and self.chatbot_id:
                cb = self.chatbot_db_util.get_chatbot(self.chatbot_id)
                selected_schema = (cb or {}).get("schema_name")
        except Exception:
            selected_schema = None

        # Generate instructions based on database type
        if db_type == "postgresql":
            return get_prompt(
                "sql_generation/postgresql_instructions.txt", 
                table_list=table_list,
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False),
                schema_name=selected_schema or ""
            )
        
        elif db_type == "bigquery":
            return get_prompt(
                "sql_generation/bigquery_instructions.txt",
                project=project or "",
                dataset=dataset or "",
                table_list=table_list or "",
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False),
                intent=question or ""
            )
        
        elif db_type == "mysql":
            return get_prompt(
                "sql_generation/mysql_instructions.txt",
                table_list=table_list,
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False)
            )
        elif db_type == "mssql":
            return get_prompt(
                "sql_generation/mssql_instructions.txt",
                table_list=table_list,
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False),
                schema_name=selected_schema or ""
            )
        else:
            # SQLite (default)
            return get_prompt(
                "sql_generation/sqlite_instructions.txt", 
                table_list=table_list,
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False)
            )

    def _get_selected_schema_name(self) -> str | None:
        try:
            if self.chatbot_db_util and self.chatbot_id:
                cb = self.chatbot_db_util.get_chatbot(self.chatbot_id)
                return (cb or {}).get("schema_name")
        except Exception:
            return None
        return None

    def _qualify_table(self, db_type: str, table_name: str, schema_name: str | None) -> str:
        if not schema_name or db_type not in ("postgresql", "mssql"):
            return f'"{table_name}"' if db_type != "bigquery" else f'`{table_name}`'
        if db_type == "postgresql":
            return f'"{schema_name}"."{table_name}"'
        if db_type == "mssql":
            return f'[{schema_name}].[{table_name}]'
        return table_name

    def _ensure_schema_qualification(self, sql: str, db_type: str, schema_name: str | None) -> str:
        if not schema_name or db_type not in ("postgresql", "mssql"):
            return sql
        import re as _re
        def _qualify(match):
            kw = match.group(1)
            ident = match.group(2)
            rest = match.group(3) or ""
            # If already qualified or quoted with schema, leave
            if '.' in ident or ident.startswith('"') or ident.startswith('['):
                return f"{kw} {ident}{rest}"
            if db_type == "postgresql":
                qualified = f'"{schema_name}"."{ident}"'
            else:
                qualified = f'[{schema_name}].[{ident}]'
            return f"{kw} {qualified}{rest}"

        # Qualify identifiers in FROM and JOIN clauses when unqualified
        pattern = _re.compile(r"\b(FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)(\s+AS\b|\s+|$)", _re.IGNORECASE)
        sql = _re.sub(pattern, _qualify, sql)
        return sql

    def _extract_sql_from_response(self, response):
        """Extract clean SQL from LLM response, removing markdown fences and explanations."""
        try:
            # Convert response to string
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            # Remove markdown code fences
            import re
            import json as _json

            # Try to parse JSON-shaped outputs and extract { "sql": "..." }
            try:
                maybe_json_text = response_text.strip()
                if maybe_json_text.startswith('{') and maybe_json_text.endswith('}'):
                    obj = _json.loads(maybe_json_text)
                    if isinstance(obj, dict) and 'sql' in obj and isinstance(obj['sql'], str):
                        response_text = obj['sql']
            except Exception:
                pass

            # Remove ```sql and ``` markers
            response_text = re.sub(
                r'```sql\s*', '', response_text, flags=re.IGNORECASE)
            response_text = re.sub(
                r'```\s*$', '', response_text, flags=re.IGNORECASE)

            # Remove any leading/trailing whitespace
            response_text = response_text.strip()

            # Prefer the substring starting at the first SELECT keyword
            m = re.search(r'\bSELECT\b', response_text, flags=re.IGNORECASE)
            if m:
                response_text = response_text[m.start():]

            # Drop any leading narrator text like "Generated SQL:" or bullets before SELECT
            response_text = re.sub(r'^(Generated\s+SQL\s*:\s*)', '', response_text, flags=re.IGNORECASE)

            # Keep only up to the final semicolon if present; otherwise use whole
            semicolon_pos = response_text.rfind(';')
            if semicolon_pos != -1:
                candidate = response_text[:semicolon_pos + 1]
            else:
                candidate = response_text

            # Collapse excessive whitespace
            candidate = re.sub(r'\s+', ' ', candidate).strip()

            # If we still don't see a SELECT and FROM, fallback to best-effort token filter
            if not re.search(r'\bSELECT\b', candidate, flags=re.IGNORECASE):
                lines = response_text.split('\n')
                sql_lines = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('--'):
                        continue
                    if any(k in line.upper() for k in ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']):
                        sql_lines.append(line)
                if sql_lines:
                    candidate = ' '.join(sql_lines)

            final_sql = candidate.strip()

            # Final spacing normalization for glued tokens around major keywords
            KEYWORDS = (
                r"(SELECT|FROM|WHERE|GROUP\s+BY|HAVING|QUALIFY|ORDER\s+BY|LIMIT|WINDOW|"
                r"JOIN|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+OUTER\s+JOIN|CROSS\s+JOIN|ON|"
                r"AND|OR)"
            )
            final_sql = re.sub(rf"([A-Za-z0-9_`\.\)])({KEYWORDS})\\b", r"\1 \2", final_sql, flags=re.IGNORECASE)
            final_sql = re.sub(r",(\S)", r", \1", final_sql)

            return final_sql.strip()

        except Exception as e:
            logging.info(f"Error extracting SQL from response: {e}")
            # Fallback to original response
            if hasattr(response, 'content'):
                return response.content
            return str(response)

    def run(self, state: dict, app_db_util=None, chatbot_db_util=None):
        try:
            # Use passed-in db utils if provided, else use instance
            app_db_util = app_db_util or self.app_db_util
            chatbot_db_util = chatbot_db_util or self.chatbot_db_util


            # Extract the latest human question (ignore system messages we added)
            question = None
            for msg in reversed(state.get("messages", [])):
                # Handle LangChain message objects
                if hasattr(msg, "content") and hasattr(msg, "__class__"):
                    content = str(msg.content)
                    class_name = msg.__class__.__name__
                    
                    # Skip system messages we added (INTENT: and CLIPPED:)
                    if class_name == "SystemMessage" and (content.startswith("INTENT:") or content.startswith("CLIPPED:")):
                        continue
                    
                    # Look for HumanMessage
                    if class_name == "HumanMessage":
                        question = content
                        break
                
                # Handle dict messages (fallback)
                elif isinstance(msg, dict):
                    content = msg.get("content", "")
                    if msg.get("role") == "system" and (content.startswith("INTENT:") or content.startswith("CLIPPED:")):
                        continue
                    if msg.get("role") == "human" and "content" in msg:
                        question = msg["content"]
                        break
            
            # If still no question found, look for any non-system message
            if question is None:
                for msg in reversed(state.get("messages", [])):
                    if hasattr(msg, "content") and hasattr(msg, "__class__"):
                        class_name = msg.__class__.__name__
                        if class_name != "SystemMessage":
                            question = str(msg.content)
                            break
                    elif isinstance(msg, dict) and msg.get("role") != "system" and "content" in msg:
                        question = msg["content"]
                        break
            
            # Final fallback: try to get question from state directly
            if question is None:
                question = state.get("question") or state.get("user_question") or "No question found"

            # Detect database type
            db_type = self._get_database_type()
            # Defer building db_instructions until after we extract intent/clipped
            db_instructions = None

            # Recover intent and clipped context from system messages (get the LATEST ones)
            intent = {}
            clipped = {}
            
            # Simple approach: look for the last INTENT and CLIPPED messages
            messages = state.get("messages", [])
            
            # Find the last INTENT message
            for msg in reversed(messages):
                content_str = None
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str) and c.startswith("INTENT:"):
                        content_str = c
                elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                    c = getattr(msg, "content")
                    if c.startswith("INTENT:"):
                        content_str = c
                
                if content_str:
                    import json as _json
                    try:
                        intent = _json.loads(content_str[7:])
                        break
                    except Exception as e:
                        break
            
            # Find the last CLIPPED message
            for msg in reversed(messages):
                content_str = None
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str) and c.startswith("CLIPPED:"):
                        content_str = c
                elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                    c = getattr(msg, "content")
                    if c.startswith("CLIPPED:"):
                        content_str = c
                
                if content_str:
                    import json as _json
                    try:
                        clipped = _json.loads(content_str[8:])
                        break
                    except Exception as e:
                        break

            
            intent_tables = intent.get('tables') or []
            intent_columns = intent.get('columns') or []
            intent_text = f"INTENT TABLES: {intent_tables}\nINTENT COLUMNS: {intent_columns}\nFILTERS: {intent.get('filters')}\nJOINS: {intent.get('joins')}\nORDER_BY: {intent.get('order_by')}\nDATE_RANGE: {intent.get('date_range')}"

            # Now that we have clipped context, build database-specific instructions
            if db_instructions is None:
                try:
                    db_instructions = self._get_database_specific_instructions(
                        db_type, 
                        clipped_context=clipped, 
                        question=question
                    )
                except Exception as e:
                    logging.warning(f"Database prompt generation failed for {db_type}: {e}")
                    # Fallback to basic instructions
                    if db_type == "bigquery":
                        db_instructions = """You are an expert SQL generator for Google BigQuery (Standard SQL).

CRITICAL RULES:
1. Use backticks for all identifiers: `table`, `column`
2. Qualify ALL columns with table aliases: t.`column`
3. Use proper JOIN syntax: FROM table1 AS t1 INNER JOIN table2 AS t2 ON t1.`key` = t2.`key`
4. Put each clause on separate lines: SELECT, FROM, JOIN...ON, WHERE, GROUP BY, ORDER BY
5. Use BigQuery date functions: EXTRACT(YEAR FROM CAST(col AS DATE))
6. For SAP tables: EBAN(BANFN,BNFPO) ↔ EKPO(BANFN,BNFPO); EKPO.EBELN ↔ EKKO.EBELN
7. MAKE SURE TO GIVE PROPER SPACING BETWEEN WORDS IN THE SQL COMMAND. DO NOT MERGE WORDS TOGETHER AS IT WILL CAUSE ERRORS AND THE QUERY WONT EXECUTE. FOR EXAMPLE, 'EKKO.EBELNWHERE' IS WRONG, INSTEAD IT SHOULD BE 'EKKO.EBELN WHERE'. THIS IS VERY IMPORTANT.

Output ONLY the final SQL query, no explanations."""
                    else:
                        db_instructions = f"You are an expert SQL generator for {db_type.upper()}. Generate valid SQL queries with proper syntax and JOINs. Output only the SQL query."

            # Sample data is disabled per requirement
            selected_sample_text = ""
            
            # Build a deterministic, DB-agnostic FROM/JOIN scaffold to reduce malformed SQL
            def _build_from_join_scaffold() -> str:
                try:
                    if not intent_tables:
                        return ""
                    # Base table (preserve exact casing)
                    base_table = str(intent_tables[0])
                    selected_schema = self._get_selected_schema_name()
                    qualified_base = self._qualify_table(db_type, base_table, selected_schema)
                    scaffold_parts = [f"FROM {qualified_base} AS {base_table}"]
                    joins_spec = intent.get('joins') or []

                    # Helper to backtick qualified identifiers in ON strings
                    import re as _re
                    def _normalize_on(on_str: str) -> str:
                        if not isinstance(on_str, str):
                            return ""
                        # Keep as "Table.Column" without dialect-specific quoting
                        return _re.sub(r"\s+", " ", on_str.strip())

                    for j in joins_spec:
                        table_name = None
                        on_clause = None
                        join_keyword = "INNER JOIN"
                        if isinstance(j, dict):
                            # Support both {table1, table2, on} and {table, join_table, on}
                            table_name = j.get('table2') or j.get('join_table') or j.get('table') or j.get('table1')
                            on_clause = j.get('on')
                            if isinstance(j.get('type'), str):
                                # Optionally use provided join type
                                join_keyword = f"{j.get('type').strip().upper()} JOIN"
                        elif isinstance(j, str):
                            # Try to parse table names from a string like "EKPO.EBELN = EKKO.EBELN"
                            m = _re.search(r"\b([A-Za-z0-9_]+)\.[A-Za-z0-9_\s]+\s*=\s*([A-Za-z0-9_]+)\.[A-Za-z0-9_\s]+", j)
                            if m:
                                # Prefer the RHS table if it's different from base
                                rhs = m.group(2)
                                lhs = m.group(1)
                                table_name = rhs if rhs != base_table else lhs
                            on_clause = j
                        if table_name:
                            t = str(table_name)
                            qualified_join = self._qualify_table(db_type, t, selected_schema)
                            on_txt = _normalize_on(on_clause or "")
                            if on_txt:
                                scaffold_parts.append(f"{join_keyword} {qualified_join} AS {t} ON {on_txt}")
                            else:
                                # Leave an explicit placeholder ON to force the model to fill it
                                scaffold_parts.append(f"{join_keyword} {qualified_join} AS {t} ON /* FILL_JOIN_CONDITION */ 1=1")

                    return "\n".join(scaffold_parts)
                except Exception:
                    return ""

            from_join_scaffold = _build_from_join_scaffold()

            # Derive allowed tables strictly from clipped context to prevent drift
            allowed_tables = sorted(list((clipped.get('tables') or {}).keys()))
            allowed_tables_str = ", ".join([f'"{t}"' for t in allowed_tables]) if allowed_tables else ""

            # Determine relationship limit based on prompt size estimation
            relationships = clipped.get('relationships', [])
            # Start with 10 relationships, but reduce if needed
            relationship_limit = 10
            
            # Create clipped context with limited relationships
            clipped_limited = clipped.copy()
            clipped_limited['relationships'] = relationships[:relationship_limit]
            clipped_text = f"CLIPPED CONTEXT: {clipped_limited}"
            
            # Build prompt once with appropriate relationship limit
            enhanced_prompt = f"""You are a SQL query generator. Your task is to convert natural language questions into SQL queries.
{self.prompt_template}
DATABASE TYPE: {db_type.upper()}
{db_instructions}

STRICT REQUIREMENTS:
- Use ONLY these tables: {allowed_tables_str if allowed_tables_str else 'None'}
- If required tables/columns are not available, output exactly "NOT FOUND"
- Never reference tables/columns outside the provided context
 - Preserve the FROM/JOIN SCAFFOLD exactly if provided (do not delete or alter JOIN order).

INTENT ANALYSIS:
{intent_text}

AVAILABLE CONTEXT:
{clipped_text}

 FROM/JOIN SCAFFOLD (MANDATORY TO KEEP UNCHANGED):
 {from_join_scaffold if from_join_scaffold else '(no scaffold available)'}

QUESTION: {question}

INSTRUCTIONS:
 1. Analyze the question and intent to understand what data is needed
 2. Use the provided FROM/JOIN SCAFFOLD verbatim (do not change it). If no scaffold shown, you must include a correct FROM base table and JOIN ... ON ... blocks.
 3. Add SELECT (with qualified columns), WHERE (if filters exist), GROUP BY (for any non-aggregated columns), ORDER BY, and LIMIT as needed.
 4. Generate syntactically correct {db_type.upper()} SQL.
 5. Use proper table aliases for clarity and qualify all columns.
 6. Preserve identifiers' casing and spacing exactly as shown in context/samples.

Generate the SQL query:"""

            # Use invoke() for LLM call with timeout handling
            try:
                print(f"[Query_Generator] Calling LLM with prompt length: {len(enhanced_prompt)} (using {relationship_limit} relationships)")
                print(enhanced_prompt)
                response = self.llm.invoke(enhanced_prompt)
                print(f"[Query_Generator] LLM response received")
            except Exception as e:
                logging.error(f"LLM call failed: {e}")
                return {"messages": ["Error generating SQL query. Please try again."]}

            # Extract and clean SQL from response
            sql = self._extract_sql_from_response(response)

            # Post-process: if scaffold exists but LLM omitted or broke it, inject/replace deterministically
            try:
                import re as _re
                if from_join_scaffold:
                    # If no FROM present, append scaffold
                    if not _re.search(r"\bFROM\b", sql, flags=_re.IGNORECASE):
                        sql = sql.strip().rstrip(';') + "\n" + from_join_scaffold
                    else:
                        # Replace the entire FROM... (until WHERE/GROUP/ORDER/HAVING/LIMIT or end) with scaffold
                        sql = _re.sub(r"\bFROM\b[\s\S]*?(?=\bWHERE\b|\bGROUP\b|\bORDER\b|\bHAVING\b|\bLIMIT\b|$)", from_join_scaffold, sql, flags=_re.IGNORECASE)
            except Exception:
                pass

            # Enforce schema qualification in final SQL as a last guard
            try:
                selected_schema = self._get_selected_schema_name()
                sql = self._ensure_schema_qualification(sql, db_type, selected_schema)
            except Exception:
                pass

            try:
                print(f"[Query_Generator] Generated SQL: {sql[:1000]}")
            except Exception:
                pass

            return {"messages": [sql]}
        except Exception as e:
            raise QueryGenerationException(e)
