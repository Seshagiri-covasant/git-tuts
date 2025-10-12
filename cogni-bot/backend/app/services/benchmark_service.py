from flask import current_app, request
from marshmallow import ValidationError

from .. import constants
from ..schemas import api_schemas
from ..utils.exceptions import ServiceException
from ..benchmark_tools.benchmark import run_benchmark as run_benchmark_logic, run_custom_tests as run_custom_tests_logic
from .chatbot_service import get_chatbot_with_validation, get_chatbot_db, validate_chatbot_status


def start_benchmark_service(chatbot_id: str):
    """Starts a new standard benchmark run. Parses request internally."""
    try:
        data = api_schemas.BenchmarkRunSchema().load(
            request.get_json(silent=True) or {})
        temperature = data.get('temperature')
        force = data.get('force')
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id, fresh_db=True)

    allowed_statuses = ["llm_configured", "template_configured", "ready"]
    if chatbot.get("status") not in allowed_statuses:
        raise ServiceException(
            f"Chatbot must be in one of {allowed_statuses}. Current status: {chatbot.get('status')}", 412)

    llm_name = chatbot.get("current_llm_name")
    effective_temp = temperature if temperature is not None else chatbot.get(
        "temperature", 0.7)

    db = get_chatbot_db()
    with db.db_engine.connect() as conn:
        result = conn.execute(
            db.test_queries_table.select().where(
                (db.test_queries_table.c.chatbot_id == chatbot_id) &
                (db.test_queries_table.c.regen_llm_name == llm_name) &
                (db.test_queries_table.c.regen_temperature == effective_temp) &
                (db.test_queries_table.c.generated_sql != None)
            )
        ).first()
        if result and not force:
            return {
                "message": "Benchmark already exists for this chatbot, LLM, and temperature.",
                "chatbot_id": chatbot_id, "llm_name": llm_name,
                "temperature": effective_temp, "benchmark_status": "exists"
            }

    db_url = chatbot.get("db_url")
    db_type = chatbot.get("db_type")
    if not db_url or not db_type:
        raise ServiceException(
            "Database not configured for this chatbot.", 400)

    status_cache = current_app.config.get('BENCHMARK_STATUS', {})
    status_cache[chatbot_id] = {
        'status': 'running', 'stage': 'Starting benchmark...', 'progress': 0,
        'llm_name': llm_name, 'temperature': effective_temp
    }

    if not db.get_conversation_by_name(chatbot_id, constants.BENCHMARK_CONVERSATION_NAME):
        db.create_conversation(
            chatbot_id, constants.BENCHMARK_CONVERSATION_NAME, "active",
            constants.BENCHMARK_CONVERSATION_OWNER, conversationType="PINNED"
        )

    executor = current_app.extensions['executor']
    executor.submit(run_benchmark_logic, chatbot_id,
                    db_url, db_type, effective_temp)

    return {
        "message": "Benchmark started successfully.", "chatbot_id": chatbot_id,
        "temperature_used": effective_temp, "force": force
    }


def get_benchmark_status_service(chatbot_id: str):
    """Gets benchmark status. Parses request args internally."""
    get_chatbot_with_validation(chatbot_id)
    llm_name = request.args.get('llm_name')
    temperature = request.args.get('temperature', type=float)

    if llm_name:
        return get_benchmark_details_service(chatbot_id, llm_name, temperature)

    status_cache = current_app.config.get('BENCHMARK_STATUS', {})
    if status := status_cache.get(chatbot_id):
        return status

    db = get_chatbot_db()
    result = db.execute_query(
        """
        SELECT COUNT(*) as count, regen_llm_name, regen_temperature, MAX(created_at) as last_run
        FROM test_queries WHERE chatbot_id = :cid AND generated_sql IS NOT NULL AND score IS NOT NULL
        GROUP BY regen_llm_name, regen_temperature ORDER BY last_run DESC LIMIT 1
        """, {"cid": chatbot_id}, fetch_one=True
    )
    if result and result.get('count', 0) > 0:
        return {"status": "completed", "message": "Benchmark data exists in database", **result}

    raise ServiceException(
        "No benchmark has been run for this chatbot yet.", 404)


def get_benchmark_details_service(chatbot_id: str, llm_name: str = None, temperature: float = None):
    """Gets detailed benchmark results. Parses request args internally if needed."""
    chatbot = get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()

    llm_name_arg = llm_name or request.args.get('llm_name')
    temp_arg = temperature if temperature is not None else request.args.get(
        'temperature', type=float)

    base_query = """
        SELECT original_sql, generated_question, generated_sql, score, regen_llm_name, regen_temperature
        FROM test_queries
        WHERE chatbot_id = :cid 
        AND generated_sql IS NOT NULL AND generated_sql != ''
        AND regen_llm_name IS NOT NULL AND regen_llm_name != 'Unknown'
        AND regen_temperature IS NOT NULL
    """
    params = {"cid": chatbot_id}

    if llm_name_arg:
        base_query += " AND regen_llm_name = :llm"
        params["llm"] = llm_name_arg
    if temp_arg is not None:
        base_query += " AND regen_temperature = :temp"
        params["temp"] = temp_arg

    base_query += " ORDER BY regen_llm_name, regen_temperature, question_id"
    details = db.execute_query(base_query, params, fetch_all=True)

    response = {"chatbot_name": chatbot.get(
        "chatbot_name") or chatbot.get("name"), "details": details}

    if llm_name_arg:
        total = len(details)
        correct = sum(1 for row in details if row.get('score') == 1)
        efficiency = (correct / total) if total > 0 else 0.0
        response["score"] = {"efficiency": efficiency,
                             "correct": correct, "total": total}
        response["llm_name"] = llm_name_arg
        if temp_arg is not None:
            response["temperature"] = temp_arg

    return response


def get_performance_metrics_service(chatbot_id: str):
    """Gets performance metrics. Parses request args internally."""
    get_chatbot_with_validation(chatbot_id)
    llm_name = request.args.get('llm_name')
    temperature = request.args.get('temperature', type=float)
    db = get_chatbot_db()
    metrics = db.get_performance_metrics(chatbot_id, llm_name, temperature)
    if metrics is None:
        raise ServiceException(
            "No performance data found for the given criteria.", 404)
    return metrics


def cleanup_benchmark_data_service(chatbot_id: str):
    """Cleans up incomplete standard benchmark data records."""
    get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()
    query = """
        DELETE FROM test_queries WHERE chatbot_id = :cid 
        AND (generated_sql IS NULL OR generated_sql = '' OR score IS NULL OR 
             regen_llm_name IS NULL OR regen_llm_name = 'Unknown' OR regen_temperature IS NULL)
    """
    db.execute_query(query, {"cid": chatbot_id})
    return {"message": "Benchmark data cleanup completed successfully", "chatbot_id": chatbot_id}

# --- Custom Test Suite Services ---


def create_custom_test_service(chatbot_id: str):
    """Creates a new custom test case. Parses request internally."""
    try:
        data = api_schemas.CustomTestCreateSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()
    return db.create_custom_test(chatbot_id, **data)


def get_custom_tests_service(chatbot_id: str):
    """Gets all custom tests for a chatbot. Parses request args internally."""
    chatbot = get_chatbot_with_validation(chatbot_id)
    test_name = request.args.get('test_name')
    db = get_chatbot_db()
    custom_tests = db.get_custom_tests(chatbot_id, test_name)
    return {"chatbot_name": chatbot.get("chatbot_name") or chatbot.get("name"), "custom_tests": custom_tests}


def get_custom_test_suites_service(chatbot_id: str):
    """Gets all unique custom test suite names for a chatbot."""
    chatbot = get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()
    test_suites = db.get_custom_test_suites(chatbot_id)
    return {"chatbot_name": chatbot.get("chatbot_name") or chatbot.get("name"), "test_suites": test_suites}


def run_custom_tests_service(chatbot_id: str):
    """Runs a suite of custom tests. Parses request internally."""
    try:
        data = api_schemas.CustomTestRunSchema().load(
            request.get_json(silent=True) or {})
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "ready")

    db = get_chatbot_db()
    custom_tests = db.get_custom_tests(chatbot_id, data.get('test_name'))
    if not custom_tests:
        raise ServiceException(
            "No custom tests found for the given criteria.", 404)

    effective_temp = data.get('temperature') if data.get(
        'temperature') is not None else chatbot.get("temperature", 0.7)

    executor = current_app.extensions['executor']
    executor.submit(run_custom_tests_logic, chatbot_id,
                    custom_tests, effective_temp)

    return {
        "message": "Custom tests started successfully",
        "test_count": len(custom_tests),
        "temperature_used": effective_temp
    }


def get_custom_test_metrics_service(chatbot_id: str):
    """Gets performance metrics for custom test runs. Parses request args internally."""
    chatbot = get_chatbot_with_validation(chatbot_id)
    test_name = request.args.get('test_name')
    llm_used = request.args.get('llm_used')
    db = get_chatbot_db()
    metrics = db.get_custom_test_metrics(chatbot_id, test_name, llm_used)
    return {
        "chatbot_name": chatbot.get("chatbot_name") or chatbot.get("name"),
        "metrics": metrics,
        "test_name": test_name,
        "llm_used": llm_used
    }


def delete_custom_test_service(test_id: str):
    """Deletes a specific custom test case by its ID."""
    db = get_chatbot_db()
    db.delete_custom_test(test_id)
    return {"message": "Custom test deleted successfully", "test_id": test_id}
