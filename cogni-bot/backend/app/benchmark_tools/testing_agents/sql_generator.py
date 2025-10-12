import logging
import re
import time
from ...utils.prompt_loader import get_prompt

logger = logging.getLogger(__name__)


class SQLGenerator:
    """
    Regenerates SQL queries from natural-language questions, using the database schema for context.
    Loads its prompt from an external file.
    """

    def __init__(self, llm_client, schema_introspector, db_type=None, max_retries=3, retry_delay=2):
        self.llm = llm_client
        self.schema = schema_introspector
        self.db_type = db_type
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def regenerate(self, question: str) -> str:
        """
        Given a natural-language question, generate a clean SQL query using the LLM.
        """
        try:
            clean_question = self._clean_question(question)
            if not clean_question:
                logger.warning(
                    "Empty or invalid question provided for SQL generation.")
                return self._generate_fallback_sql(question)

            if self.db_type is None:
                self.db_type = self._detect_database_type()

            for attempt in range(self.max_retries):
                try:
                    sql = self._generate_sql_with_llm(
                        clean_question, self.db_type)
                    if sql and self._validate_generated_sql(sql):
                        logger.debug(
                            f"Successfully generated SQL on attempt {attempt + 1}")
                        return sql
                    else:
                        logger.warning(
                            f"Generated SQL validation failed on attempt {attempt + 1}")

                except Exception as e:
                    logger.error(
                        f"Error generating SQL on attempt {attempt + 1}: {e}", exc_info=True)

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

            logger.warning(
                "All retry attempts failed, generating fallback SQL.")
            return self._generate_fallback_sql(clean_question)

        except Exception as e:
            logger.error(
                f"Critical error in SQL regeneration: {e}", exc_info=True)
            return self._generate_fallback_sql(question)

    def _clean_question(self, question: str) -> str:
        """Clean and validate the input question."""
        if not question:
            return ""

        # Remove markdown and code fences
        clean = re.sub(r'```[^`]*```', '', question)
        clean = re.sub(r'`[^`]*`', '', clean)

        # Remove extra whitespace
        clean = ' '.join(clean.split())

        # Basic validation
        if len(clean) < 5:
            return ""

        return clean.strip()

    def _detect_database_type(self) -> str:
        """Detect database type from schema introspector."""
        try:
            if hasattr(self.schema, 'db_engine'):
                db_url = str(self.schema.db_engine.url)
                if 'postgresql' in db_url.lower():
                    return "postgresql"
                elif 'sqlite' in db_url.lower():
                    return "sqlite"
                elif 'mysql' in db_url.lower():
                    return "mysql"
                elif 'oracle' in db_url.lower():
                    return "oracle"
            return "sqlite"  # default fallback
        except Exception as e:
            logger.warning(f"Could not detect database type: {e}")
            return "sqlite"

    def _generate_sql_with_llm(self, question: str, db_type: str) -> str:
        """Generate SQL using the LLM with database-specific instructions from files."""
        try:
            # Build the dynamic part of the prompt
            base_prompt_text = (
                f"You have the following {db_type.upper()} database schema:\n{self.schema}\n\n"
                f"Convert the following natural-language question into a valid {db_type.upper()} SQL query.\n"
                f"QUESTION: {question}\n\n"
            )

            # Load the static instruction set from the corresponding file
            if db_type == "postgresql":
                instructions = get_prompt(
                    "sql_generation/postgresql_instructions.txt", table_list="<placeholder>")
            elif db_type == "bigquery":
                instructions = get_prompt(
                    "sql_generation/bigquery_instructions.txt", table_list="<placeholder>")
            else:  # SQLite
                instructions = get_prompt(
                    "sql_generation/sqlite_instructions.txt", table_list="<placeholder>")

            # Clean up the instructions as we don't need the table list part here
            instructions = re.sub(
                r'- IMPORTANT: Use only these exact table names:.*?(\n|$)', '', instructions).strip()

            prompt = base_prompt_text + instructions

            response = self.llm.invoke(prompt)
            sql = self._extract_sql_from_response(response)

            return sql

        except Exception as e:
            logger.error(f"Error generating SQL with LLM: {e}")
            return None

    def _extract_sql_from_response(self, response) -> str:
        """Extract SQL from LLM response with multiple fallback methods."""
        try:
            # Extract content from response
            if hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            elif hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'message'):
                response_text = response.message
            else:
                response_text = str(response)

            if not response_text:
                return None

            # Clean the response
            sql = response_text.strip()

            # Remove markdown code fences
            sql = re.sub(r'```(?:sql)?', '', sql)

            # Remove any explanatory text before or after SQL
            lines = sql.split('\n')
            sql_lines = []
            in_sql = False

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check if this line looks like SQL
                if re.match(r'^(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)', line, re.IGNORECASE):
                    in_sql = True

                if in_sql:
                    sql_lines.append(line)

                # Stop if we hit explanatory text after SQL
                if in_sql and line.startswith(('The query', 'This SQL', 'The result', 'Note:', 'Explanation:')):
                    break

            sql = ' '.join(sql_lines).strip()

            # Basic validation
            if not sql or len(sql) < 10:
                return None

            return sql

        except Exception as e:
            logger.error(f"Error extracting SQL from response: {e}")
            return None

    def _validate_generated_sql(self, sql: str) -> bool:
        """Basic validation of generated SQL."""
        if not sql:
            return False

        # Check for basic SQL structure
        sql_upper = sql.upper()

        # Must have SELECT
        if 'SELECT' not in sql_upper:
            return False

        # Must have FROM
        if 'FROM' not in sql_upper:
            return False

        # Check for balanced parentheses
        if sql.count('(') != sql.count(')'):
            return False

        # Check for reasonable length
        if len(sql) < 10 or len(sql) > 5000:
            return False

        return True

    def _generate_fallback_sql(self, question: str) -> str:
        """Generate a simple fallback SQL when LLM fails."""
        try:
            # Extract potential table names from question
            words = question.lower().split()
            table_keywords = ['table', 'from', 'in', 'of']
            potential_table = None

            for i, word in enumerate(words):
                if word in table_keywords and i + 1 < len(words):
                    potential_table = words[i + 1]
                    break

            if not potential_table:
                potential_table = "data"

            # Generate simple fallback query
            fallback_sql = f'SELECT * FROM "{potential_table}" LIMIT 10'

            logger.info(f"Generated fallback SQL: {fallback_sql}")
            return fallback_sql

        except Exception as e:
            logger.error(f"Error generating fallback SQL: {e}")
            return 'SELECT 1'  # Ultimate fallback
