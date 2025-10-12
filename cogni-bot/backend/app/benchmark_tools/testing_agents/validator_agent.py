import logging
from sqlalchemy import text
import time
from typing import Optional, Union
from langchain_core.language_models import BaseLanguageModel
from ...utils.prompt_loader import get_prompt

logger = logging.getLogger(__name__)


class ValidatorAgent:
    """
    Validates SQL queries using LLM-based functional equivalence checking.
    """

    def __init__(self, app_db_util, llm: Optional[BaseLanguageModel] = None, timeout=30):
        self.app_db_util = app_db_util
        self.llm = llm
        self.timeout = timeout
        self.db_type = self._detect_database_type()

    def compare(self, original_sql: str, generated_sql: str, nl_question: str = "") -> str:
        """
        Compare two SQL queries using LLM. Returns "yes", "no", or "ambiguous".
        """
        try:
            if not original_sql or not generated_sql:
                return "no"

            clean_original = self._clean_sql(original_sql)
            clean_generated = self._clean_sql(generated_sql)

            if clean_original == clean_generated:
                logger.debug(
                    f"Queries are identical after cleaning. Result: yes")
                return "yes"

            if self.llm:
                return self._llm_based_comparison(clean_original, clean_generated, nl_question)
            else:
                logger.warning(
                    "No LLM provided for validation. Cannot compare non-identical queries.")
                return "no"  # Fallback if no LLM is available for non-identical queries

        except Exception as e:
            logger.error(f"Error comparing SQL queries: {e}", exc_info=True)
            return "no"

    def _llm_based_comparison(self, original_sql: str, generated_sql: str, nl_question: str) -> str:
        """Use LLM to determine functional equivalence between two SQL queries."""
        try:
            # The prompt loader was incorrect in your file, it should be validate_sql.txt
            prompt = get_prompt(
                "benchmarking/sql_validation.txt",
                nl_question=nl_question,
                original_sql=original_sql,
                generated_sql=generated_sql,
                db_type=self.db_type
            )

            response = self.llm.invoke(prompt)

            result = (response.content if hasattr(response, 'content')
                      else str(response)).strip().lower()
            result = result.replace('.', '').replace(
                '"', '').replace("'", "").strip()

            # Make the check more robust
            if result.startswith("yes"):
                return "yes"
            if result.startswith("no"):
                return "no"

            logger.warning(
                f"Unexpected LLM validation response: '{result}', defaulting to 'ambiguous'.")
            return "ambiguous"

        except Exception as e:
            logger.error(f"Error in LLM-based comparison: {e}", exc_info=True)
            return "no"

    def _detect_database_type(self):
        """Detect the database type from the connection URL."""
        try:
            db_url = str(self.app_db_util.db_engine.url)
            if 'postgresql' in db_url.lower():
                return "postgresql"
            elif 'sqlite' in db_url.lower():
                return "sqlite"
            elif 'mysql' in db_url.lower():
                return "mysql"
            elif 'oracle' in db_url.lower():
                return "oracle"
            else:
                return "unknown"
        except Exception as e:
            logger.warning(f"Could not detect database type: {e}")
            return "unknown"

    def _clean_sql(self, sql):
        """Clean and normalize SQL query."""
        if not sql:
            return ""

        # Remove markdown code fences
        sql = sql.replace('```sql', '').replace('```', '').strip()

        # Remove trailing semicolon if present
        if sql.endswith(';'):
            sql = sql[:-1].strip()

        # Normalize whitespace
        sql = ' '.join(sql.split())

        return sql

    def _execute_query_with_timeout(self, sql):
        """
        Execute SQL query with timeout protection.
        Returns the result set or None if execution fails.
        """
        try:
            start_time = time.time()

            with self.app_db_util.db_engine.connect() as conn:
                # Set timeout for the connection
                if self.db_type == "postgresql":
                    conn.execute(text("SET statement_timeout = :timeout"), {
                                 "timeout": self.timeout * 1000})
                elif self.db_type == "mysql":
                    conn.execute(text("SET SESSION max_execution_time = :timeout"), {
                                 "timeout": self.timeout * 1000})

                # Execute the query
                result = conn.execute(text(sql))

                # Check if we exceeded timeout
                if time.time() - start_time > self.timeout:
                    logger.warning(
                        f"Query execution exceeded timeout of {self.timeout} seconds")
                    return None

                # Fetch all results
                rows = result.fetchall()

                # Convert to list of dictionaries for easier comparison
                if rows:
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    return []

        except Exception as e:
            logger.error(f"Error executing query '{sql}': {e}")
            return None

    def _normalize_result(self, result):
        """
        Normalize query results for comparison.
        Handles different data types and formats.
        """
        if not result:
            return []

        try:
            normalized = []
            for row in result:
                normalized_row = {}
                for key, value in row.items():
                    # Normalize data types
                    if value is None:
                        normalized_row[str(key)] = None
                    elif isinstance(value, (int, float)):
                        normalized_row[str(key)] = float(value)
                    elif isinstance(value, str):
                        normalized_row[str(key)] = value.strip()
                    else:
                        normalized_row[str(key)] = str(value)
                normalized.append(normalized_row)

            # Sort by all keys to ensure consistent comparison
            if normalized:
                keys = sorted(normalized[0].keys())
                normalized = [sorted(row.items()) for row in normalized]
                normalized.sort()

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing result: {e}")
            return result

    def validate_single_query(self, sql):
        """
        Validate a single SQL query by attempting to execute it.
        Returns True if query executes successfully, False otherwise.
        """
        try:
            if not sql:
                return False

            sql = self._clean_sql(sql)
            result = self._execute_query_with_timeout(sql)
            return result is not None

        except Exception as e:
            logger.error(f"Error validating query '{sql}': {e}")
            return False

    def get_query_info(self, sql):
        """
        Get information about a query without executing it.
        Returns a dictionary with query analysis.
        """
        try:
            if not sql:
                return {"error": "Empty SQL provided"}

            sql = self._clean_sql(sql)

            info = {
                "sql": sql,
                "length": len(sql),
                "has_select": "SELECT" in sql.upper(),
                "has_from": "FROM" in sql.upper(),
                "has_join": "JOIN" in sql.upper(),
                "has_where": "WHERE" in sql.upper(),
                "has_group_by": "GROUP BY" in sql.upper(),
                "has_order_by": "ORDER BY" in sql.upper(),
                "has_limit": "LIMIT" in sql.upper(),
                "database_type": self.db_type
            }

            return info

        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            return {"error": str(e)}
