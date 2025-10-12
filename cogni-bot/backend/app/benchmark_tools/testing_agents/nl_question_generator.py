import uuid
import re
import logging
from ...utils.prompt_loader import get_prompt

logger = logging.getLogger(__name__)


class NLQuestionGenerator:
    """
    Generates 5 distinct NL questions (1 basic, 2 medium, 2 complex) by prompting the LLM with the schema.
    Stores only the NL questions in the DB (no SQL yet).
    """

    def __init__(self, llm_client, schema_introspector, chatbot_db_util):
        self.llm = llm_client
        self.introspector = schema_introspector
        self.chatbot_db = chatbot_db_util

    def generate(self, chatbot_id, llm_name, db_schema, temperature=0.7, db_type=None):
        """
        Generate NL questions with robust error handling and database type detection.
        """
        try:
            # Use provided db_type or detect from schema introspector
            if db_type is None:
                db_type = self._detect_database_type()

            prompt = get_prompt(
                "benchmarking/generate_nl_questions.txt",
                db_type=db_type.upper(),
                db_schema=db_schema
            )

            logger.info(
                f"Generating NL questions for chatbot {chatbot_id} with {db_type} database")
            response = self.llm.invoke(prompt)

            # Extract response content with fallback
            response_text = self._extract_response_content(response)
            if not response_text:
                logger.error("Failed to get response from LLM")
                return self._generate_fallback_questions(db_schema)

            # Parse questions with improved regex
            questions = self._parse_questions(response_text)

            # Ensure we have exactly 5 questions, generate fallbacks if needed
            if len(questions) < 5:
                logger.warning(
                    f"Only got {len(questions)} questions, generating fallbacks")
                fallback_questions = self._generate_fallback_questions(
                    db_schema)
                questions.extend(fallback_questions[:5-len(questions)])

            # Store questions in database with error handling
            self._store_questions(chatbot_id, llm_name, temperature, questions)

            logger.info(
                f"Successfully generated {len(questions)} NL questions for chatbot {chatbot_id}")
            return questions

        except Exception as e:
            logger.error(
                f"Error generating NL questions for chatbot {chatbot_id}: {e}")
            # Generate fallback questions if everything fails
            fallback_questions = self._generate_fallback_questions(db_schema)
            self._store_questions(chatbot_id, llm_name,
                                  temperature, fallback_questions)
            return fallback_questions

    def _detect_database_type(self):
        """Detect database type from schema introspector."""
        try:
            if hasattr(self.introspector, 'db_engine'):
                db_url = str(self.introspector.db_engine.url)
                if 'postgresql' in db_url.lower():
                    return "postgresql"
                elif 'sqlite' in db_url.lower():
                    return "sqlite"
                elif 'mysql' in db_url.lower():
                    return "mysql"
                elif 'oracle' in db_url.lower():
                    return "oracle"
            return "database"  # fallback
        except Exception as e:
            logger.warning(f"Could not detect database type: {e}")
            return "database"

    def _extract_response_content(self, response):
        """Extract content from LLM response with multiple fallbacks."""
        try:
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            elif hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'message'):
                return response.message
            else:
                return str(response)
        except Exception as e:
            logger.error(f"Error extracting response content: {e}")
            return None

    def _parse_questions(self, response_text):
        """Parse questions from response text with improved regex."""
        try:
            # Clean response text
            clean_resp = re.sub(r'```(?:sql)?', '', response_text)

            # Multiple patterns to catch different formats
            patterns = [
                r'QUESTION:\s*(?P<question>.*?)(?=---|$)',  # Original pattern
                # Q: or Q1: format
                r'Q[:\d]*\s*(?P<question>.*?)(?=\n\n|\nQ|\n---|$)',
                # Just the question
                r'^\s*(?P<question>.*?)(?=\n\n|\nQ|\n---|$)',
            ]

            questions = []
            for pattern in patterns:
                matches = re.finditer(
                    pattern, clean_resp, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    question_text = match.group('question').strip()
                    # Minimum length check
                    if question_text and len(question_text) > 10:
                        questions.append(question_text)
                if questions:  # If we found questions with this pattern, use them
                    break

            return questions[:5]  # Limit to 5 questions

        except Exception as e:
            logger.error(f"Error parsing questions: {e}")
            return []

    def _generate_fallback_questions(self, db_schema):
        """Generate fallback questions when LLM fails."""
        try:
            # Extract table names from schema
            table_names = re.findall(
                r'CREATE TABLE\s+"?(\w+)"?', db_schema, re.IGNORECASE)
            if not table_names:
                table_names = re.findall(
                    r'Table\s+"?(\w+)"?', db_schema, re.IGNORECASE)

            if not table_names:
                table_names = ["data"]  # fallback

            fallback_questions = [
                f"How many records are in the {table_names[0]} table?",
                f"What are the top 5 records from {table_names[0]}?",
                f"Show me all columns from {table_names[0]}",
                f"Count the total number of records in {table_names[0]}",
                f"Display the first 10 records from {table_names[0]}"
            ]

            return fallback_questions[:5]

        except Exception as e:
            logger.error(f"Error generating fallback questions: {e}")
            return [
                "How many records are in the database?",
                "Show me the first 5 records",
                "What are all the columns available?",
                "Count the total number of records",
                "Display sample data from the database"
            ]

    def _store_questions(self, chatbot_id, llm_name, temperature, questions):
        """Store questions in database with error handling."""
        try:
            with self.chatbot_db.db_engine.begin() as conn:
                for q in questions:
                    conn.execute(self.chatbot_db.test_queries_table.insert().values(
                        query_id=str(uuid.uuid4()),
                        question_id=str(uuid.uuid4()),
                        chatbot_id=chatbot_id,
                        llm_using=llm_name,
                        temperature=temperature,
                        generated_question=q,
                        original_sql=None,
                        generated_sql=None,
                        score=None,
                        regen_llm_name=None,
                        regen_temperature=None
                    ))
            logger.info(f"Stored {len(questions)} questions in database")
        except Exception as e:
            logger.error(f"Error storing questions in database: {e}")
            raise
