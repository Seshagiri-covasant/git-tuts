import logging
import time
import uuid
import re
from sqlalchemy import text
from flask import current_app

from .. import constants
from ..utils.exceptions import ServiceException
from ..benchmark_tools.testing_agents.sql_generator import SQLGenerator
from ..benchmark_tools.testing_agents.validator_agent import ValidatorAgent
from ..benchmark_tools.testing_agents.nl_question_generator import NLQuestionGenerator
from ..benchmark_tools.testing_agents.original_sql_generator import OriginalSQLGenerator
from ..repositories.chatbot_db_util import ChatbotDbUtil
from ..repositories.app_db_util import AppDbUtil
from ..utils.schema_extractor import extract_schema_from_db
from ..agents.llm_factory import get_llm

logger = logging.getLogger(__name__)

# --- Helper Functions ---


def _post_to_test_suite(chatbot_id: str, message: str):
    """Posts a system message to the 'Test Suite' conversation."""
    try:
        db = ChatbotDbUtil()
        conversation = db.get_conversation_by_name(
            chatbot_id, constants.BENCHMARK_CONVERSATION_NAME)

        if not conversation:
            logger.debug(
                f"Could not find '{constants.BENCHMARK_CONVERSATION_NAME}' conversation for chatbot {chatbot_id} to post status.")
            return

        db.create_interaction(
            conversation.get("conversationId"),
            request_text=message,
            is_system_message=True
        )
        db.db_engine.dispose()
    except Exception as e:
        logger.error(
            f"Failed to post message to Test Suite for chatbot {chatbot_id}: {e}", exc_info=True)


def _update_status(chatbot_id: str, status: str, stage: str = None, progress: float = None, result: dict = None, llm_name: str = None, temperature: float = None):
    """Safely updates benchmark status in the app's shared config and posts to the test suite."""
    if not current_app:
        logger.error(
            "Cannot update benchmark status: Flask application context is not available.")
        return

    status_cache = current_app.config.get('BENCHMARK_STATUS', {})

    entry = status_cache.get(chatbot_id, {})
    entry['status'] = status
    if stage is not None:
        entry['stage'] = stage
    if progress is not None:
        entry['progress'] = progress
    if result is not None:
        entry['result'] = result
    if llm_name is not None:
        entry['llm_name'] = llm_name
    if temperature is not None:
        entry['temperature'] = temperature

    status_cache[chatbot_id] = entry

    log_progress = round(
        progress * 100) if progress is not None else entry.get('progress')
    message = f"Status: {status}"
    if stage:
        message += f" - Stage: {stage}"
    if log_progress is not None:
        message += f" - Progress: {log_progress}%"

    _post_to_test_suite(chatbot_id, message)
    logger.info(f"BENCHMARK_UPDATE for {chatbot_id}: {message}")


def _get_chatbot_info(chatbot_id: str) -> dict:
    """Fetches chatbot config from a background thread and disposes of the connection."""
    db = ChatbotDbUtil()
    chatbot = db.get_chatbot(chatbot_id)
    db.db_engine.dispose()
    if not chatbot:
        raise ServiceException(
            f"Benchmark failed: Chatbot not found: {chatbot_id}", 404)
    return chatbot


def _get_app_db(cfg: dict) -> AppDbUtil:
    """Returns an AppDbUtil instance from a background thread."""
    db_url = cfg.get("db_url")
    credentials_json = cfg.get("credentials_json")
    if not db_url:
        raise ServiceException(
            f"Benchmark failed: App DB not configured for {cfg.get('chatbot_id')}", 400)
    return AppDbUtil(db_url, credentials_json=credentials_json)

# --- Main Background Task ---


def run_benchmark(chatbot_id: str, db_url: str, db_type: str, temperature: float = None):
    """The main function to execute the full benchmark process for a chatbot."""
    chatbot_db = None
    app_db = None
    llm_name = "Unknown"

    try:
        chatbot_cfg = _get_chatbot_info(chatbot_id)
        llm_name = chatbot_cfg.get("current_llm_name")
        if temperature is None:
            temperature = chatbot_cfg.get("temperature", 0.7)

        _update_status(chatbot_id, 'running', 'Starting benchmark...',
                       0.0, llm_name=llm_name, temperature=temperature)

        chatbot_db = ChatbotDbUtil()
        app_db = _get_app_db(chatbot_cfg)

        _update_status(chatbot_id, 'running', 'Extracting schema',
                       0.05, llm_name=llm_name, temperature=temperature)
        schema = extract_schema_from_db(
            db_url, db_type, chatbot_cfg.get("credentials_json"))
        llm_client = get_llm(llm_name, temperature=temperature)

        # Step 2: Generate NL Questions
        with chatbot_db.db_engine.connect() as conn:
            nl_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM test_queries WHERE chatbot_id = :cid"), {"cid": chatbot_id}
            ).scalar_one_or_none() or 0
        if nl_count == 0:
            _update_status(chatbot_id, 'running', 'Generating NL questions',
                           0.1, llm_name=llm_name, temperature=temperature)
            nl_gen = NLQuestionGenerator(llm_client, schema, chatbot_db)
            nl_gen.generate(chatbot_id, llm_name, schema,
                            temperature=temperature, db_type=db_type)

        # Step 3: Generate Original SQL
        with chatbot_db.db_engine.connect() as conn:
            missing_sql_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM test_queries WHERE chatbot_id = :cid AND original_sql IS NULL"), {"cid": chatbot_id}
            ).scalar_one_or_none() or 0
        if missing_sql_count > 0:
            _update_status(chatbot_id, 'running', 'Generating original SQL',
                           0.2, llm_name=llm_name, temperature=temperature)
            orig_sql_gen = OriginalSQLGenerator(llm_client, schema, chatbot_db)
            orig_sql_gen.generate(
                chatbot_id, llm_name, schema, temperature=temperature, db_type=db_type)

        # Step 4: Regenerate SQL
        sql_gen = SQLGenerator(llm_client, schema, db_type=db_type)
        with chatbot_db.db_engine.connect() as conn:
            rows_to_process = conn.execute(
                text("""
                    SELECT DISTINCT t1.question_id, t1.generated_question, t1.original_sql, t1.llm_using, t1.temperature
                    FROM test_queries t1 WHERE t1.chatbot_id = :cid AND t1.original_sql IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM test_queries t2 WHERE t2.chatbot_id = :cid 
                        AND t2.question_id = t1.question_id AND t2.regen_llm_name = :llm AND t2.regen_temperature = :temp
                    )
                """),
                {"cid": chatbot_id, "llm": llm_name, "temp": temperature}
            ).fetchall()

            total_questions = len(rows_to_process)
            logger.info(
                f"Found {total_questions} questions to process for this benchmark run.")
            for idx, row in enumerate(rows_to_process, 1):
                progress = 0.3 + (0.5 * (idx / total_questions))
                _update_status(
                    chatbot_id, 'running', f'Regenerating SQL ({idx}/{total_questions})', progress, llm_name=llm_name, temperature=temperature)

                new_sql = sql_gen.regenerate(row.generated_question)

                with chatbot_db.db_engine.begin() as insert_conn:
                    insert_conn.execute(chatbot_db.test_queries_table.insert().values(
                        query_id=str(uuid.uuid4()), question_id=row.question_id, chatbot_id=chatbot_id,
                        llm_using=row.llm_using, temperature=row.temperature, original_sql=row.original_sql,
                        generated_question=row.generated_question, generated_sql=new_sql, score=None,
                        regen_llm_name=llm_name, regen_temperature=temperature
                    ))
                time.sleep(0.5)

        # Step 5: Validate and score
        _update_status(chatbot_id, 'running', 'Validating queries',
                       0.8, llm_name=llm_name, temperature=temperature)
        validator = ValidatorAgent(app_db, llm_client)
        with chatbot_db.db_engine.begin() as conn:
            rows_to_validate = conn.execute(
                text("SELECT query_id, original_sql, generated_sql, generated_question FROM test_queries WHERE chatbot_id = :cid AND regen_llm_name = :llm AND regen_temperature = :temp AND score IS NULL"),
                {"cid": chatbot_id, "llm": llm_name, "temp": temperature}
            ).fetchall()

            logger.info(f"Found {len(rows_to_validate)} queries to validate.")
            for row in rows_to_validate:
                validation_result = validator.compare(
                    row.original_sql, row.generated_sql, row.generated_question)
                score = 1 if validation_result == "yes" else 0
                conn.execute(
                    text(
                        "UPDATE test_queries SET score = :score, llm_validation_result = :val_res WHERE query_id = :qid"),
                    {"score": score, "val_res": validation_result, "qid": row.query_id}
                )

        # Step 6: Finalize
        _update_status(chatbot_id, 'running', 'Calculating final score',
                       0.99, llm_name=llm_name, temperature=temperature)
        with chatbot_db.db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) AS total, SUM(score) AS correct FROM test_queries WHERE chatbot_id = :cid AND regen_llm_name = :llm AND regen_temperature = :temp"),
                {"cid": chatbot_id, "llm": llm_name, "temp": temperature}
            ).fetchone()

        total = result.total if result else 0
        correct = result.correct if result and result.correct else 0
        efficiency = (correct / total) if total > 0 else 0.0

        logger.info(
            f"Benchmark complete. Score: {correct}/{total} ({efficiency*100:.2f}%)")
        final_result = {"efficiency": efficiency*100, "correct": correct,
                        "total": total, "llm_name": llm_name, "temperature": temperature}
        _update_status(chatbot_id, 'completed', 'Benchmark finished', 1.0,
                       result=final_result, llm_name=llm_name, temperature=temperature)
        chatbot_db.update_chatbot(chatbot_id=chatbot_id, efficiency=efficiency)

    except Exception as e:
        logger.error(
            f"Error running benchmark for {chatbot_id}: {e}", exc_info=True)
        _update_status(chatbot_id, 'error',
                       f'Benchmark failed: {str(e)}', 1.0, llm_name=llm_name, temperature=temperature)
    finally:
        if app_db:
            app_db.db_engine.dispose()
        if chatbot_db:
            chatbot_db.db_engine.dispose()
        logger.info(f"--- Finished Benchmark for Chatbot ID: {chatbot_id} ---")


def run_custom_tests(chatbot_id: str, custom_tests: list, temperature: float):
    """Executes a suite of custom-defined tests for a chatbot in a background thread."""
    chatbot_db = None
    app_db = None
    try:
        logger.info(f"Starting custom tests for chatbot_id={chatbot_id}...")
        chatbot_cfg = _get_chatbot_info(chatbot_id)
        llm_name = chatbot_cfg.get("current_llm_name")
        db_type = chatbot_cfg.get("db_type")

        chatbot_db = ChatbotDbUtil()
        app_db = _get_app_db(chatbot_cfg)
        llm_client = get_llm(llm_name, temperature=temperature)

        schema = extract_schema_from_db(
            chatbot_cfg["db_url"], db_type, chatbot_cfg.get("credentials_json"))
        validator = ValidatorAgent(app_db, llm_client)

        total_tests = len(custom_tests)
        correct_tests = 0

        for i, test in enumerate(custom_tests):
            test_id = test.get('test_id')
            if not test_id:
                logger.warning(
                    f"Skipping custom test at index {i} due to missing test_id.")
                continue

            try:
                natural_question = test['natural_question']
                original_sql = test['original_sql']

                prompt = (
                    f"You are an expert SQL generator. Given the database schema below, "
                    f"convert the user's question into a valid SQL query for a {db_type} database.\n\n"
                    f"SCHEMA:\n{schema}\n\n"
                    f"USER QUESTION: {natural_question}\n\n"
                    f"SQL QUERY:"
                )

                response = llm_client.invoke(prompt)

                generated_sql = str(response.content if hasattr(
                    response, 'content') else response).strip()
                generated_sql = re.sub(
                    r'```(?:sql)?', '', generated_sql, flags=re.IGNORECASE | re.DOTALL).strip()

                validation_result = validator.compare(
                    original_sql, generated_sql, natural_question)
                score = 1 if validation_result == "yes" else 0
                if score == 1:
                    correct_tests += 1

                chatbot_db.update_custom_test_result(
                    test_id=test_id,
                    generated_sql=generated_sql,
                    score=score,
                    llm_used=llm_name,
                    temperature=temperature,
                    llm_validation_result=validation_result
                )
                logger.info(
                    f"Custom Test {i+1}/{total_tests} (ID: {test_id}): {'PASS' if score == 1 else 'FAIL'}")

            except Exception as e:
                logger.error(
                    f"Error processing custom test {test_id}: {e}", exc_info=True)
                chatbot_db.update_custom_test_result(
                    test_id=test_id,
                    generated_sql="ERROR: Generation or validation failed.",
                    score=0,
                    llm_used=llm_name,
                    temperature=temperature,
                    llm_validation_result="error"
                )

        efficiency = (correct_tests / total_tests) if total_tests > 0 else 0.0
        logger.info(
            f"Custom tests completed for chatbot {chatbot_id}: "
            f"{correct_tests}/{total_tests} correct ({efficiency:.2%})"
        )

    except Exception as e:
        logger.error(
            f"A critical error occurred while running custom tests for {chatbot_id}: {e}", exc_info=True)
    finally:
        if app_db:
            app_db.db_engine.dispose()
        if chatbot_db:
            chatbot_db.db_engine.dispose()
        logger.info(
            f"Cleaned up resources for custom test run on chatbot {chatbot_id}.")
