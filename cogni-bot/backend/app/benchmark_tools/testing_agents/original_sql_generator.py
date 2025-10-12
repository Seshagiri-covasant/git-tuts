import logging
import re
import time
from ...utils.prompt_loader import get_prompt

logger = logging.getLogger(__name__)


class OriginalSQLGenerator:
    """
    For each NL question in the DB (with empty original_sql), generate SQL using the LLM and schema, and store it in original_sql.
    Supports multiple database types with robust error handling and retry logic.
    """

    def __init__(self, llm_client, schema_introspector, chatbot_db_util, max_retries=3, retry_delay=2):
        self.llm = llm_client
        self.schema = schema_introspector
        self.chatbot_db = chatbot_db_util
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def generate(self, chatbot_id, llm_name, db_schema, temperature=0.7, db_type=None):
        """
        Generate original SQL for NL questions with robust error handling.
        """
        try:
            # Use provided db_type or detect from schema introspector
            if db_type is None:
                db_type = self._detect_database_type()
            logger.info(
                f"Generating original SQL for chatbot {chatbot_id} with {db_type} database")

        # Fetch NL questions with empty original_sql
            questions = self._fetch_questions_needing_sql(chatbot_id)
            if not questions:
                logger.info(
                    f"No questions need original SQL generation for chatbot {chatbot_id}")
                return

            logger.info(
                f"Found {len(questions)} questions needing original SQL generation")

            # Process each question
            for question_row in questions:
                try:
                    question_id = question_row.question_id
                    nl_question = question_row.generated_question

                    logger.debug(
                        f"Generating SQL for question: {nl_question[:50]}...")

                    # Generate SQL with retry logic
                    sql = self._generate_sql_with_retries(
                        nl_question, db_schema, db_type)

                    if sql:
                        # Store the generated SQL
                        self._store_generated_sql(question_id, sql)
                        logger.debug(
                            f"Successfully generated and stored SQL for question {question_id}")
                    else:
                        logger.warning(
                            f"Failed to generate SQL for question {question_id}")

                except Exception as e:
                    logger.error(
                        f"Error processing question {question_row.question_id}: {e}")
                    continue

            logger.info(
                f"Completed original SQL generation for chatbot {chatbot_id}")

        except Exception as e:
            logger.error(
                f"Critical error in original SQL generation for chatbot {chatbot_id}: {e}")
            raise

    def _detect_database_type(self):
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

    def _fetch_questions_needing_sql(self, chatbot_id):
        """Fetch questions that need original SQL generation."""
        try:
            with self.chatbot_db.db_engine.connect() as conn:
                rows = conn.execute(
                    self.chatbot_db.test_queries_table.select().where(
                        (self.chatbot_db.test_queries_table.c.chatbot_id == chatbot_id) &
                        (self.chatbot_db.test_queries_table.c.original_sql == None)
                    )
                ).fetchall()
            return rows
        except Exception as e:
            logger.error(f"Error fetching questions needing SQL: {e}")
            return []

    def _generate_sql_with_retries(self, nl_question, db_schema, db_type):
        """Generate SQL with retry logic and fallback mechanisms."""
        for attempt in range(self.max_retries):
            try:
                sql = self._generate_sql_with_llm(
                    nl_question, db_schema, db_type)
                if sql and self._validate_generated_sql(sql):
                    logger.debug(
                        f"Successfully generated SQL on attempt {attempt + 1}")
                    return sql
                else:
                    logger.warning(
                        f"Generated SQL validation failed on attempt {attempt + 1}")

            except Exception as e:
                logger.error(
                    f"Error generating SQL on attempt {attempt + 1}: {e}")

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.debug(f"Waiting {wait_time} seconds before retry")
                time.sleep(wait_time)

        # If all retries failed, generate fallback SQL
        logger.warning("All retry attempts failed, generating fallback SQL")
        return self._generate_fallback_sql(nl_question)

    def _generate_sql_with_llm(self, nl_question, db_schema, db_type):
        """Generate SQL using the LLM with database-specific instructions."""
        try:
            # Build the initial part of the prompt
            base_prompt_text = (
                f"You have the following {db_type.upper()} database schema:\n{db_schema}\n\n"
                f"Convert the following natural-language question into a valid {db_type.upper()} SQL query.\n"
                f"QUESTION: {nl_question}\n\n"
            )

            # Load the specific instruction set from a file
            if db_type == "postgresql":
                instructions = get_prompt(
                    "sql_generation/postgresql_instructions.txt", table_list="<table_list_placeholder>")
            elif db_type == "bigquery":
                instructions = get_prompt(
                    "sql_generation/bigquery_instructions.txt", table_list="<table_list_placeholder>")
            else:  # Default to SQLite
                instructions = get_prompt(
                    "sql_generation/sqlite_instructions.txt", table_list="<table_list_placeholder>")

            instructions = re.sub(
                r'- IMPORTANT: Use only these exact table names:.*?(\n|$)', '', instructions).strip()

            # Combine the parts to form the final prompt
            prompt = base_prompt_text + instructions

            response = self.llm.invoke(prompt)
            sql = self._extract_sql_from_response(response)

            return sql

        except Exception as e:
            logger.error(f"Error generating SQL with LLM: {e}")
            return None

    def _extract_sql_from_response(self, response):
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

    def _validate_generated_sql(self, sql):
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

    def _generate_fallback_sql(self, question):
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

    def _store_generated_sql(self, question_id, sql):
        """Store the generated SQL in the database."""
        try:
            with self.chatbot_db.db_engine.begin() as conn:
                conn.execute(
                    self.chatbot_db.test_queries_table.update()
                    .where(self.chatbot_db.test_queries_table.c.question_id == question_id)
                    .values(original_sql=sql)
                )
        except Exception as e:
            logger.error(
                f"Error storing generated SQL for question {question_id}: {e}")
            raise
