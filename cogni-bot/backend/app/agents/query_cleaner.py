import re


class QueryCleaner:
    def __init__(self, app_db_util=None, chatbot_db_util=None):
        self.app_db_util = app_db_util  # For application DB operations
        # For chatbot-related data (chat_bot.db)
        self.chatbot_db_util = chatbot_db_util

    def run(self, state: dict, app_db_util=None, chatbot_db_util=None):
        # Use passed-in db utils if provided, else use instance
        app_db_util = app_db_util or self.app_db_util
        chatbot_db_util = chatbot_db_util or self.chatbot_db_util
        # Clean the last message if it's a string or has 'content'
        msg = state["messages"][-1]
        if hasattr(msg, "content"):
            sql = msg.content
        elif isinstance(msg, dict) and "content" in msg:
            sql = msg["content"]
        else:
            sql = str(msg)
        # Remove triple backticks and optional 'sql' after them
        sql = re.sub(r"^```sql\s*|^```|```$", "", sql.strip(),
                     flags=re.IGNORECASE | re.MULTILINE)
        # Remove any remaining backticks anywhere
        sql = sql.replace("```", "").strip()
        # Check for forbidden DML/DDL commands
        forbidden = re.compile(
            r"\b(insert|update|delete|alter|drop|create|truncate|replace)\b", re.IGNORECASE)
        if forbidden.search(sql):
            # Add a flag to indicate forbidden SQL and the error message
            state["forbidden_sql"] = True
            state["messages"][-1] = "Sorry, I'm not allowed to run data-modification or DDL commands (like INSERT, UPDATE, DELETE, ALTER, DROP, CREATE, TRUNCATE, REPLACE). Please ask me to query data instead."
            return state

        # Strip any accidental commentary that the LLM might append after a semicolon
        # Keep only the first SQL statement when semicolon appears followed by non-SQL text.
        # Example: "SELECT ...; However, based on ..." -> keep before ';'
        if ";" in sql:
            parts = sql.split(";")
            # Heuristic: keep the first non-empty part as SQL; re-append semicolon if originally present
            first_stmt = parts[0].strip()
            if first_stmt:
                sql = first_stmt

        # IMPORTANT: do not change identifier casing here; we will preserve the
        # exact casing as provided by the upstream agents (intent/context/sample data).

        # Extra hardening pass to fix common formatting leaks
        try:
            # Ensure a space before major SQL keywords and operators (fixes EKKO.EBELNWHERE, EBELPAND, etc.)
            KEYWORDS = (
                r"(SELECT|FROM|WHERE|GROUP\s+BY|HAVING|ORDER\s+BY|LIMIT|WINDOW|"
                r"JOIN|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+OUTER\s+JOIN|CROSS\s+JOIN)"
            )
            sql = re.sub(rf"([A-Za-z0-9_`\.\)])({KEYWORDS})\\b", r"\1 \2", sql, flags=re.IGNORECASE)

            # Ensure JOIN variants are not glued to previous tokens (e.g., FROMINNER JOIN)
            sql = re.sub(r"\bFROM\s*(INNER|LEFT|RIGHT|FULL\s+OUTER|CROSS)?\s*JOIN\b", 
                         lambda m: "FROM " + (m.group(1) + " " if m.group(1) else "") + "JOIN",
                         sql, flags=re.IGNORECASE)

            # Insert a space after commas where missing
            sql = re.sub(r",(\S)", r", \1", sql)

            #insert exactly one space before & after KEYWORDS
            sql = re.sub(rf"\s*({KEYWORDS})\s*", r" \1 ", sql, flags=re.IGNORECASE)

            # kill duplicated FROM/JOIN aliases
            sql = re.sub(r"\b(AS\s+([A-Za-z][A-Za-z0-9_]*))\s+\2\b", r"\1", sql, flags=re.IGNORECASE)
            # EXTRACT(): remove leaked alias after FROM
            sql = re.sub(r"EXTRACT\(\s*(YEAR|MONTH|DAY)\s+FROM\s+([^)]+?)\s+AS\s+[A-Za-z][A-Za-z0-9_]*\s*\)",
                         r"EXTRACT(\1 FROM \2)", sql, flags=re.IGNORECASE)
            
            # Fix PARSE_DATE double percent signs (%%d-%%m-%%Y -> %d-%m-%Y)
            sql = re.sub(r"PARSE_DATE\s*\(\s*'%%([^']+)'\s*,", r"PARSE_DATE('%\1',", sql, flags=re.IGNORECASE)
            
            # Normalize excessive spaces
            sql = re.sub(r"\s+", " ", sql)
            sql = sql.strip()
        except Exception:
            pass

        # Replace the last message with the cleaned SQL
        state["forbidden_sql"] = False
        state["messages"][-1] = sql
        state["generated_sql"] = sql
        state["sql_query"] = sql
        state["sql"] = sql  # Add this for query validator/executor
        state["query"] = sql  # Add this for query validator/executor
        state["final_sql"] = sql  # Add this for query validator/executor
        
        try:
            print(f"[Query_Cleaner] Cleaned SQL: {sql[:1000]}")
            print(f"[Query_Cleaner] State keys after cleaning: {list(state.keys())}")
            print(f"[Query_Cleaner] State.generated_sql: {state.get('generated_sql', 'NOT SET')[:100] if state.get('generated_sql') else 'NOT SET'}")
        except Exception:
            pass
        
        # CRITICAL: Return the updated state properly for LangGraph
        return {
            **state,
            "messages": state["messages"],
            "generated_sql": sql,
            "sql_query": sql,
            "sql": sql,
            "query": sql,
            "final_sql": sql
        }
