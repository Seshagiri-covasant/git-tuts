from ..utils.exceptions import QueryGenerationException
from sqlalchemy import text
import logging


class QueryValidatorAgent:
    def __init__(self, llm, app_db_util=None, chatbot_db_util=None):
        self.llm = llm
        self.app_db_util = app_db_util  # For application DB (query validation)
        self.chatbot_db_util = chatbot_db_util

    def _validate_sql_syntax(self, sql_query, db_type="postgresql"):
        """Validate SQL syntax using EXPLAIN/dry-run to get precise error feedback."""
        try:
            if not self.app_db_util:
                return True, "No database connection available for validation"
            
            # Detect database type if not provided
            if not db_type:
                db_url = str(self.app_db_util.db_engine.url)
                if 'postgresql' in db_url or 'postgres://' in db_url:
                    db_type = "postgresql"
                elif 'bigquery://' in db_url:
                    db_type = "bigquery"
                elif 'mysql' in db_url:
                    db_type = "mysql"
                elif 'mssql' in db_url:
                    db_type = "mssql"
                else:
                    db_type = "sqlite"
            
            with self.app_db_util.db_engine.connect() as conn:
                if db_type.lower() == "postgresql":
                    # Use EXPLAIN for PostgreSQL - this validates syntax without executing
                    explain_query = f"EXPLAIN {sql_query}"
                    conn.execute(text(explain_query))
                    return True, "SQL syntax is valid"
                
                elif db_type.lower() == "sqlite":
                    # Use EXPLAIN for SQLite - this validates syntax without executing
                    explain_query = f"EXPLAIN {sql_query}"
                    conn.execute(text(explain_query))
                    return True, "SQL syntax is valid"
                
                elif db_type.lower() == "bigquery":
                    # For BigQuery, use dry-run validation to check syntax without executing
                    try:
                        # Try to use BigQuery's dry-run feature if available
                        dry_run_query = f"SELECT * FROM ({sql_query}) WHERE FALSE"
                        conn.execute(text(dry_run_query))
                        return True, "SQL syntax is valid"
                    except Exception as dry_run_error:
                        # If dry-run fails, try basic validation
                        conn.execute(text(sql_query))
                        return True, "SQL syntax is valid"
                elif db_type.lower() == "mysql":
                    # MySQL: EXPLAIN validates syntax
                    explain_query = f"EXPLAIN {sql_query}"
                    conn.execute(text(explain_query))
                    return True, "SQL syntax is valid"
                elif db_type.lower() == "mssql":
                    # MSSQL: TRY basic execution in a TOP 0 wrapper when possible
                    wrapped = f"SELECT * FROM ( {sql_query} ) AS _t WHERE 1=0"
                    conn.execute(text(wrapped))
                    return True, "SQL syntax is valid"
                
                else:
                    # Fallback to basic validation for other DB types
                    conn.execute(text(sql_query))
                    return True, "SQL syntax is valid"
                    
        except Exception as e:
            # Extract the specific error message from the database
            error_msg = str(e)
            
            # Enhance error message for better LLM feedback
            if "syntax error" in error_msg.lower():
                import re
                # Extract line and position info for syntax errors
                line_match = re.search(r'LINE (\d+):', error_msg)
                if line_match:
                    line_num = line_match.group(1)
                    error_msg = f"Syntax error at line {line_num}: {error_msg}"
                else:
                    error_msg = f"Syntax error: {error_msg}"
                
                # Check for specific common BigQuery syntax errors
                if "expected end of input but got keyword by" in error_msg.lower():
                    error_msg = "CRITICAL SYNTAX ERROR: Missing 'GROUP' keyword before 'BY'. Check for merged keywords like 'EKKOGROUP BY' - should be 'GROUP BY' on separate line."
                elif "group by" in sql_query.lower() and "groupby" in sql_query.lower():
                    error_msg = "CRITICAL SYNTAX ERROR: Keywords merged together. 'GROUPBY' should be 'GROUP BY' (two separate words)."
                elif re.search(r'\w+GROUP\s+BY', sql_query, re.IGNORECASE):
                    error_msg = "CRITICAL SYNTAX ERROR: Table alias merged with 'GROUP BY'. Each clause must be on its own line with proper spacing."
                    
            elif "column" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_msg = f"Column reference error: {error_msg}"
            elif "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_msg = f"Table reference error: {error_msg}"
            
            return False, error_msg

    def _repair_join_scaffold(self, sql_query: str, intent: dict) -> str:
        """Best-effort fix for malformed JOIN scaffolding while preserving identifiers' casing.
        - Fixes patterns like: 'FROM INNER JOIN' -> 'FROM <first_table> INNER JOIN'
        - Fixes patterns like: 'INNER JOIN ON'   -> 'INNER JOIN <next_table> ON'
        Uses INTENT.TABLES order and INTENT.JOINS to infer missing table tokens.
        """
        try:
            if not sql_query:
                return sql_query

            repaired = sql_query
            tables = intent.get('tables') or []
            joins = intent.get('joins') or []

            # Normalize whitespace for pattern checks (but keep original spacing in replacements)
            import re

            # 1) FROM INNER JOIN -> FROM <first_table> INNER JOIN
            if tables:
                first_table = str(tables[0])
                repaired = re.sub(r"\bFROM\s+INNER\s+JOIN\b", f"FROM {first_table} INNER JOIN", repaired, flags=re.IGNORECASE)

            # 1b) FROM (missing table) e.g., 'FROM GROUP BY' or 'FROM WHERE' etc.
            # Try to infer base table from the first qualified reference like 'eban.`...`' or 'eban.'
            m_from_missing = re.search(r"\bFROM\s+(?=GROUP\b|ORDER\b|WHERE\b|HAVING\b|LIMIT\b)", repaired, flags=re.IGNORECASE)
            if m_from_missing:
                base_alias_match = re.search(r"\b([A-Za-z0-9_]+)\.`[A-Za-z0-9_\s]+`|\b([A-Za-z0-9_]+)\.[A-Za-z0-9_]+", repaired)
                base_table = None
                if base_alias_match:
                    alias = base_alias_match.group(1) or base_alias_match.group(2)
                    # Map alias to an intent table by lowercased name
                    for t in tables:
                        if str(t).lower() == alias.lower():
                            base_table = str(t)
                            break
                if not base_table and tables:
                    base_table = str(tables[0])
                if base_table:
                    repaired = re.sub(r"\bFROM\s+(?=GROUP\b|ORDER\b|WHERE\b|HAVING\b|LIMIT\b)", f"FROM {base_table} ", repaired, flags=re.IGNORECASE)

            # 2) INNER JOIN ON -> INNER JOIN <next_table> ON
            # Use join specs to pick the RHS table name in order
            next_table = None
            if joins:
                j0 = joins[0]
                # joins can be dicts with 'table2' or strings; handle both
                if isinstance(j0, dict) and j0.get('table2'):
                    next_table = str(j0['table2'])
                elif isinstance(j0, str):
                    # Try to extract RHS table from a pattern like 'A.B = C.D'
                    m = re.search(r"\b([A-Za-z0-9_]+)\.[A-Za-z0-9_]+\s*=\s*([A-Za-z0-9_]+)\.[A-Za-z0-9_]+", j0)
                    if m:
                        next_table = m.group(2)
            if next_table:
                repaired = re.sub(r"\bINNER\s+JOIN\s+ON\b", f"INNER JOIN {next_table} ON", repaired, flags=re.IGNORECASE)

            # 3) JOIN <table> <cond starting with alias.>  -> JOIN <table> ON <cond>
            # Handles cases where ON keyword is missing entirely
            repaired = re.sub(r"\b(JOIN|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+OUTER\s+JOIN)\s+(`?[A-Za-z0-9_]+`?)\s+((?:[A-Za-z0-9_`]+)\.)",
                              r"\1 \2 ON \3", repaired, flags=re.IGNORECASE)

            # 4) Remove trailing comma before ORDER BY/GROUP BY/HAVING/LIMIT
            repaired = re.sub(r",\s+(ORDER\b|GROUP\b|HAVING\b|LIMIT\b)", r" \1", repaired, flags=re.IGNORECASE)

            return repaired
        except Exception:
            return sql_query

    def _normalize_identifier_casing(self, sql_query: str, intent: dict) -> str:
        """Rewrite identifiers to match exact casing from INTENT tables/columns.
        - Table names in backticks: `ekko` -> `EKKO`
        - Qualified columns: e.`bedat` or EKKO.BEDAT -> preserve column part casing as in INTENT columns.
        Does not add/remove identifiers; best-effort replacements only when a case-insensitive match exists in INTENT.
        """
        try:
            if not sql_query:
                return sql_query
            import re

            tables = intent.get('tables') or []
            cols = intent.get('columns') or []
            lc_table_to_exact = {str(t).lower(): str(t) for t in tables}

            # Map lowercased column name (no table prefix) to exact casing from intent
            lc_col_to_exact = {}
            for c in cols:
                cs = str(c)
                if '.' in cs:
                    _, col = cs.split('.', 1)
                else:
                    col = cs
                lc_col_to_exact[col.lower()] = col

            normalized = sql_query

            # 1) Normalize backticked table names
            def _replace_table(m):
                ident = m.group(1)
                exact = lc_table_to_exact.get(ident.lower())
                return f"`{exact}`" if exact else m.group(0)
            normalized = re.sub(r"`([A-Za-z0-9_]+)`", _replace_table, normalized)

            # 1b) Normalize bare table names after FROM/JOIN to backticked exact casing
            def _replace_from_table(m):
                ident = m.group(1)
                exact = lc_table_to_exact.get(ident.lower())
                return f"FROM `{exact}`" if exact else m.group(0)
            normalized = re.sub(r"\bFROM\s+([A-Za-z0-9_]+)\b", _replace_from_table, normalized)

            def _replace_join_table(m):
                ident = m.group(1)
                exact = lc_table_to_exact.get(ident.lower())
                return f"JOIN `{exact}`" if exact else m.group(0)
            normalized = re.sub(r"\bJOIN\s+([A-Za-z0-9_]+)\b", _replace_join_table, normalized)

            # 2) Normalize backticked qualified columns: alias.`col` -> alias.`COL` (as per intent)
            def _replace_qual_col_bt(m):
                alias = m.group(1)
                col = m.group(2)
                exact_col = lc_col_to_exact.get(col.lower())
                if exact_col:
                    return f"{alias}.`{exact_col}`"
                return m.group(0)
            normalized = re.sub(r"\b([A-Za-z0-9_]+)\.`([A-Za-z0-9_]+)`", _replace_qual_col_bt, normalized)

            # 3) Normalize unquoted qualified columns: alias.COL -> alias.COL (adjust case only)
            def _replace_qual_col_unq(m):
                alias = m.group(1)
                col = m.group(2)
                exact_col = lc_col_to_exact.get(col.lower())
                if exact_col:
                    return f"{alias}.{exact_col}"
                return m.group(0)
            normalized = re.sub(r"\b([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\b", _replace_qual_col_unq, normalized)

            return normalized
        except Exception:
            return sql_query

    def _repair_group_by_syntax(self, sql_query: str) -> str:
        """Repair common GROUP BY syntax errors in BigQuery."""
        try:
            import re
            
            # Fix merged table alias with GROUP BY: "EKKOGROUP BY" -> "GROUP BY"
            sql_query = re.sub(r'(\w+)GROUP\s+BY', r'\1\nGROUP BY', sql_query, flags=re.IGNORECASE)
            
            # Fix merged keywords: "GROUPBY" -> "GROUP BY"
            sql_query = re.sub(r'GROUPBY', 'GROUP BY', sql_query, flags=re.IGNORECASE)
            
            # Fix missing space: "GROUPBY" -> "GROUP BY"
            sql_query = re.sub(r'GROUP\s*BY', 'GROUP BY', sql_query, flags=re.IGNORECASE)
            
            # Ensure GROUP BY is on its own line
            sql_query = re.sub(r'(\w+)\s+GROUP\s+BY', r'\1\nGROUP BY', sql_query, flags=re.IGNORECASE)
            
            # Fix similar issues with ORDER BY
            sql_query = re.sub(r'(\w+)ORDER\s+BY', r'\1\nORDER BY', sql_query, flags=re.IGNORECASE)
            sql_query = re.sub(r'ORDERBY', 'ORDER BY', sql_query, flags=re.IGNORECASE)
            
            return sql_query
        except Exception:
            return sql_query

    def _remove_order_by_in_subqueries_for_mssql(self, sql_query: str) -> str:
        """MSSQL disallows ORDER BY in subqueries without TOP/OFFSET. Remove inner ORDER BY clauses conservatively."""
        try:
            import re
            fixed = re.sub(r"ORDER\s+BY\s+[^)]+(?=\))", "", sql_query, flags=re.IGNORECASE)
            fixed = re.sub(r"\s+,\s*\)", ")", fixed)
            return fixed
        except Exception:
            return sql_query

    def _fix_sql_with_llm(self, sql_query, error_message, intent, clipped_context, question, db_type):
        """Use LLM to fix the SQL query based on the error."""
        try:
            # Create a focused prompt for fixing the SQL with specific error feedback
            fix_prompt = f"""You are a SQL linter. Make the SMALLEST POSSIBLE syntax edits so the SQL parses. Do NOT change meaning.

DATABASE TYPE: {db_type.upper()}

SPECIFIC ERROR FROM DATABASE EXPLAIN:
{error_message}

ORIGINAL SQL (minimally edit this):
{sql_query}

INTENT SNAPSHOT (read-only context, do not expand scope):
- Tables: {intent.get('tables', [])}
- Columns: {intent.get('columns', [])}
- Joins: {intent.get('joins', [])}
- Filters: {intent.get('filters', [])}
- Order By: {intent.get('order_by', [])}
- Date Range: {intent.get('date_range', [])}

AVAILABLE SCHEMA (CLIPPED CONTEXT):
{clipped_context}

STRICT RULES (MANDATORY):
1) Perform SYNTAX-ONLY fixes: punctuation, parentheses, alias references, quoting, dialect function names, join ON formatting.
2) DO NOT change business logic or structure: keep the same CTEs, subqueries, joins, filters, grouping, ordering, limits.
3) DO NOT introduce/remove tables, CTEs, or columns. Only adjust typos if the corrected name exists in context.
4) DO NOT rewrite from scratch or simplify. Keep original clause order and shape.
5) If more than a few tokens must change or semantics would change, RETURN THE ORIGINAL SQL UNCHANGED.
6) Use only objects present in the clipped context. If an object seems missing, prefer keeping original and fixing syntax around it.
7) Follow {db_type.upper()} dialect strictly.

Output: Return ONLY the minimally corrected SQL text, no commentary or markdown fences. If refusing per rule (5), return the original SQL verbatim."""

            print(f"[Query_Validator] Attempting to fix SQL with LLM...")
            response = self.llm.invoke(fix_prompt)
            
            # Extract the fixed SQL
            fixed_sql = self._extract_sql_from_response(response)
            print(f"[Query_Validator] Fixed SQL: {fixed_sql[:200]}...")
            
            return fixed_sql
            
        except Exception as e:
            logging.error(f"Error fixing SQL with LLM: {e}")
            return sql_query  # Return original if fixing fails

    def _extract_sql_from_response(self, response):
        """Extract clean SQL from LLM response."""
        try:
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            # Remove markdown code fences
            import re
            response_text = re.sub(r'```sql\s*', '', response_text, flags=re.IGNORECASE)
            response_text = re.sub(r'```\s*$', '', response_text, flags=re.IGNORECASE)
            response_text = response_text.strip()

            return response_text
        except Exception as e:
            logging.error(f"Error extracting SQL from response: {e}")
            return str(response)

    def run(self, state: dict, app_db_util=None, chatbot_db_util=None):
        try:
            # Use passed-in db utils if provided, else use instance
            app_db_util = app_db_util or self.app_db_util
            chatbot_db_util = chatbot_db_util or self.chatbot_db_util

            # Get the SQL query from the previous node (Query_Cleaner)
            sql_query = None
            
            # Look for the most recent message that contains SQL (from Query_Cleaner)
            for msg in reversed(state.get("messages", [])):
                content_str = None
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str):
                        content_str = c
                elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                    content_str = getattr(msg, "content")
                
                if content_str:
                    # Skip system messages we added
                    if content_str.startswith("INTENT:") or content_str.startswith("CLIPPED:"):
                        continue
                    
                    # Look for SQL-like content (contains SELECT, FROM, etc.)
                    if any(keyword in content_str.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']):
                        sql_query = content_str
                        break

            if not sql_query:
                print("[Query_Validator] No SQL query found to validate")
                return {"messages": ["No SQL query found to validate"]}

            print(f"[Query_Validator] Validating SQL: {sql_query[:100]}...")

            # Detect database type
            db_type = "sqlite"  # Default
            if app_db_util:
                db_url = str(app_db_util.db_engine.url)
                if 'postgresql' in db_url or 'postgres://' in db_url:
                    db_type = "postgresql"
                elif 'bigquery://' in db_url:
                    db_type = "bigquery"
                elif 'mysql' in db_url:
                    db_type = "mysql"
                elif 'mssql' in db_url:
                    db_type = "mssql"

            # Extract intent snapshot for potential repairs
            intent = {}
            for msg in reversed(state.get("messages", [])):
                content_str = None
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str) and c.startswith("INTENT:"):
                        import json as _json
                        try:
                            intent = _json.loads(c[7:])
                        except Exception:
                            pass
                        break
                elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                    c = getattr(msg, "content")
                    if c.startswith("INTENT:"):
                        import json as _json
                        try:
                            intent = _json.loads(c[7:])
                        except Exception:
                            pass
                        break

            # Best-effort repair malformed JOIN scaffolding before validation
            repaired_sql = self._repair_join_scaffold(sql_query, intent)
            # Repair GROUP BY syntax errors
            repaired_sql = self._repair_group_by_syntax(repaired_sql)
            # Normalize identifier casing to match INTENT tables/columns
            repaired_sql = self._normalize_identifier_casing(repaired_sql, intent)

            # MSSQL guard: strip ORDER BY inside subqueries to avoid 1033
            if db_type == "mssql":
                try:
                    repaired_sql = self._remove_order_by_in_subqueries_for_mssql(repaired_sql)
                except Exception:
                    pass

            # Validate SQL syntax using EXPLAIN/dry-run
            is_valid, error_message = self._validate_sql_syntax(repaired_sql, db_type)
            
            if is_valid:
                print("[Query_Validator] SQL syntax is valid, passing through")
                return {"messages": [repaired_sql]}
            else:
                print(f"[Query_Validator] SQL syntax error: {error_message}")
                
                # Try to fix the SQL using LLM
                # Get intent and context from state for fixing
                intent = {}
                clipped_context = {}
                
                # Find the last INTENT and CLIPPED messages
                for msg in reversed(state.get("messages", [])):
                    content_str = None
                    if isinstance(msg, dict):
                        c = msg.get("content")
                        if isinstance(c, str) and c.startswith("INTENT:"):
                            import json as _json
                            try:
                                intent = _json.loads(c[7:])
                            except Exception:
                                pass
                        elif isinstance(c, str) and c.startswith("CLIPPED:"):
                            import json as _json
                            try:
                                clipped_context = _json.loads(c[8:])
                            except Exception:
                                pass
                    elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                        c = getattr(msg, "content")
                        if c.startswith("INTENT:"):
                            import json as _json
                            try:
                                intent = _json.loads(c[7:])
                            except Exception:
                                pass
                        elif c.startswith("CLIPPED:"):
                            import json as _json
                            try:
                                clipped_context = _json.loads(c[8:])
                            except Exception:
                                pass

                # Get the original question
                question = "Unknown question"
                for msg in reversed(state.get("messages", [])):
                    if hasattr(msg, "content") and hasattr(msg, "__class__"):
                        class_name = msg.__class__.__name__
                        if class_name == "HumanMessage":
                            question = str(msg.content)
                            break

                # Fix the SQL using LLM
                fixed_sql = self._fix_sql_with_llm(repaired_sql, error_message, intent, clipped_context, question, db_type)
                
                # Validate the fixed SQL using EXPLAIN
                is_fixed_valid, fix_error = self._validate_sql_syntax(fixed_sql, db_type)
                
                if is_fixed_valid:
                    print("[Query_Validator] SQL successfully fixed and validated")
                    return {"messages": [fixed_sql]}
                else:
                    print(f"[Query_Validator] Fixed SQL still has errors: {fix_error}")
                    
                    # Try a second fix attempt with the new error
                    print("[Query_Validator] Attempting second fix with specific error feedback...")
                    second_fix = self._fix_sql_with_llm(fixed_sql, fix_error, intent, clipped_context, question, db_type)
                    
                    # Validate the second fix
                    is_second_valid, second_error = self._validate_sql_syntax(second_fix, db_type)
                    
                    if is_second_valid:
                        print("[Query_Validator] Second fix successful and validated")
                        return {"messages": [second_fix]}
                    else:
                        print(f"[Query_Validator] Second fix failed: {second_error}")
                        print("[Query_Validator] Returning original SQL after 2 failed attempts")
                        return {"messages": [sql_query]}  # Return original if both fixes failed

        except Exception as e:
            logging.error(f"Query validation failed: {e}")
            # Return the original SQL if validation fails
            return {"messages": [sql_query] if sql_query else ["Validation failed"]}
