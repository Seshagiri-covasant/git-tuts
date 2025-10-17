import logging
import re
import json
from datetime import date, datetime
from sqlalchemy import text
from ..utils.exceptions import QueryExecutionException
from decimal import Decimal


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

class CustomJsonEncoder(json.JSONEncoder):
    """
    A custom JSON encoder that handles common non-serializable types
    like datetime, date, and Decimal objects.
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            # Convert Decimal to a float for JSON compatibility.
            # Using str(obj) is also a safe alternative if you need perfect precision.
            return float(obj)
        return super().default(obj)
    

class QueryExecutor:
    def __init__(self, app_db_util=None, chatbot_db_util=None):
        self.app_db_util = app_db_util  # For application DB (query execution)
        # For chatbot data (chat_bot.db)
        self.chatbot_db_util = chatbot_db_util
        self.db_engine = self.app_db_util.get_db_conn() if self.app_db_util else None
        self.logger = logging.getLogger(__name__)

    def run(self, state: dict, app_db_util=None, chatbot_db_util=None):
        """
         Executes the query (or returns an error message) as follows:
          If state contains forbidden_sql (e.g. DDL commands), returns a forbidden error message.
          If the query (from generator) is exactly "NOT FOUND" (case-insensitive, with or without quotes), returns "Unrelevant request for this context."
          If the query result (data) is empty (i.e. no rows returned), returns "NOT FOUND" (so that queries like "pound transactions flag asth and the customer name" that return no rows display "NOT FOUND").
          If an exception (e.g. a syntax error) is caught, returns "Sorry mate, error occurred please try again" (instead of raising a QueryExecutionException).
          Otherwise, returns the query result (as a JSON string).
         """
        if state.get("forbidden_sql", False):
            error_msg = state["messages"][-1]
            return {"messages": [error_msg]}

        app_db_util = (app_db_util or self.app_db_util)
        chatbot_db_util = (chatbot_db_util or self.chatbot_db_util)
        
        # Get SQL from state (from Query_Generator or Query_Validator)
        sql = None
        if state.get("generated_sql"):
            sql = state.get("generated_sql")
            self.logger.info(f"Found SQL from state.generated_sql: {sql}")
        elif state.get("sql_query"):
            sql = state.get("sql_query")
            self.logger.info(f"Found SQL from state.sql_query: {sql}")
        else:
            # Fallback to messages
            sql = state["messages"][-1]
            self.logger.info(f"Raw SQL from state: {sql}")
            if hasattr(sql, "content"):
                sql = sql.content
                self.logger.info(f"Extracted SQL content: {sql}")
            elif isinstance(sql, dict) and "content" in sql:
                sql = sql["content"]
                self.logger.info(f"Extracted SQL from dict: {sql}")

        if isinstance(sql, str) and "not allowed to run data-modification" in sql:
            return {"messages": [sql]}

        if isinstance(sql, str) and sql.strip().replace('"', '').upper() == "NOT FOUND":
            return {"messages": ["This question is not relevant to the database domain."]}

        if "SQLQuery:" in sql:
            sql = sql.split("SQLQuery:")[-1].strip()
            self.logger.info(f"SQL after SQLQuery extraction: {sql}")
        match = re.search(r"(SELECT|INSERT|UPDATE|DELETE)\b.*",
                          sql, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(0)
            self.logger.info(f"SQL after regex extraction: {sql}")
        else:
            self.logger.warning(f"No SQL pattern found in: {sql}")
            # Skip execution if no valid SQL pattern found
            return {"messages": ["No valid SQL query found to execute"]}

        # Final safety cleanup: normalize glued tokens, enforce spacing before keywords
        try:
            KEYWORDS = (
                r"(SELECT|FROM|WHERE|GROUP\s+BY|HAVING|QUALIFY|ORDER\s+BY|LIMIT|WINDOW|"
                r"JOIN|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+OUTER\s+JOIN|CROSS\s+JOIN|ON|"
                r"AND|OR)"
            )
            sql = re.sub(rf"([A-Za-z0-9_`\.\)])({KEYWORDS})\\b", r"\1 \2", sql, flags=re.IGNORECASE)
            sql = re.sub(r",(\S)", r", \1", sql)
            sql = re.sub(r"\s+", " ", sql).strip()
        except Exception:
            pass

        try:
            self.logger.info(f"Executing SQL query: {sql}")
            self.logger.info(f"app_db_util: {app_db_util}")

            if app_db_util is None:
                self.logger.error("app_db_util is None")
                raise QueryExecutionException(
                    "Application database utility (app_db_util) is not configured. Please call /config/appdb first.")

            with app_db_util.get_db_conn() as conn:
                self.logger.info("Database connection established")
                with conn.begin():
                    self.logger.info("Executing query with SQLAlchemy text()")
                    answer = conn.execute(text(sql))
                    columns = list(answer.keys())
                    self.logger.info(
                        f"Query executed successfully. Columns: {columns}")
                    data = [dict(zip(columns, row))
                            for row in answer.fetchall()]
                    self.logger.info(f"Retrieved {len(data)} rows")

            if not data:
                self.logger.info("No data returned from query")
                return {"messages": ["I couldn't find any data matching your question in the database. Please try rephrasing your question or check if the data exists for the criteria you specified."]}

            # Create response with data and metadata
            row_count = len(data)
            response_data = {
                "data": data,
                "metadata": {
                    "row_count": row_count,
                    "columns": columns
                }
            }
            
            # --- USE THE CORRECTED ENCODER ---
            ret = {"messages": [json.dumps(response_data, cls=CustomJsonEncoder)]}
            try:
                print(f"[Query_Executor] Rows: {row_count} Sample: {json.dumps(data[:3], cls=CustomJsonEncoder)[:1000]}")
            except Exception:
                pass
            self.logger.info("Query execution completed successfully")
            return ret
        
        except Exception as e:
            self.logger.error("Error executing query: %s", str(e))
            self.logger.error("Full error details: %s", e)
            import traceback
            self.logger.error("Traceback: %s", traceback.format_exc())
            return {"messages": ["Sorry mate, error occurred please try again"]}
