import logging
from urllib.parse import quote_plus
import time
import json
from flask import current_app, request
from marshmallow import ValidationError

from ..schemas.semantic_models import DatabaseSchema


from .. import constants
from ..schemas import api_schemas
from ..repositories.chatbot_db_util import ChatbotDbUtil
from ..repositories.app_db_util import AppDbUtil
from ..models.enums import ChatbotStatus
from ..utils.exceptions import ServiceException
from ..utils.schema_extractor import SchemaExtractor
from ..utils.schema_convertor import convert_raw_schema_to_semantic

logger = logging.getLogger(__name__)


def get_chatbot_db():
    return current_app.config['PROJECT_DB']


def get_chatbot_with_validation(chatbot_id: str, fresh_db: bool = False):
    db = ChatbotDbUtil() if fresh_db else get_chatbot_db()
    chatbot = db.get_chatbot(chatbot_id)
    if not chatbot:
        raise ServiceException("Chatbot not found", 404)
    return chatbot


def validate_chatbot_status(chatbot: dict, required_status_str: str):
    required_status = ChatbotStatus(required_status_str)
    current_status_str = chatbot.get("status", ChatbotStatus.CREATED.value)
    current_status = ChatbotStatus(current_status_str)
    status_order = list(ChatbotStatus)
    if status_order.index(current_status) < status_order.index(required_status):
        raise ServiceException(
            f"Chatbot must be at least in '{required_status.value}' status. Current status: '{current_status.value}'", 412
        )


def get_all_chatbots_service():
    """Service logic for listing all chatbots."""
    db = get_chatbot_db()
    chatbots = db.get_all_chatbots()
    result = []
    for p in chatbots:
        template_name = None
        template_id = p.get("template_id")
        if template_id:
            template = db.get_template_by_id(template_id)
            if template:
                template_name = template.get("name")

        # Ensure created_at is a JSON-serializable string
        created_at_iso = p.get("created_at").isoformat() if p.get(
            "created_at") else None

        # Debug: Log what LLM name is being returned
        current_llm = p.get("current_llm_name")
        print(f"[Chatbot Service] Chatbot {p['chatbot_id']} ({p['name']}): current_llm_name = '{current_llm}'")
        
        result.append({
            "chatbot_id": p["chatbot_id"],
            "name": p["name"],
            "status": p.get("status"),
            "created_at": created_at_iso,
            "llm_name": current_llm,
            "temperature": p.get("temperature"),
            "db_type": p.get("db_type"),
        "db_url": p.get("db_url"),
        "schema_name": p.get("schema_name"),
            "template_name": template_name
        })
    return result


def create_chatbot_service():
    """Service logic for creating a chatbot. Parses request internally."""
    try:
        validated_data = api_schemas.ChatbotCreateSchema().load(request.get_json())
        name = validated_data['name']
        temperature = validated_data.get(
            'temperature', constants.DEFAULT_TEMPERATURE)
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    db = get_chatbot_db()
    return db.create_chatbot(name, status=ChatbotStatus.CREATED.value, temperature=temperature)


def get_chatbot_details_service(chatbot_id: str):
    """Service logic for getting chatbot details."""
    chatbot = get_chatbot_with_validation(chatbot_id, fresh_db=True)
    config_status = {
        "database_configured": bool(chatbot.get("db_url")),
        "llm_configured": bool(chatbot.get("current_llm_name")),
        "template_configured": bool(chatbot.get("template_id") is not None),
        "ready_for_conversations": chatbot.get("status") == ChatbotStatus.READY.value
    }
    chatbot["configuration_status"] = config_status
    if "temperature" not in chatbot:
        chatbot["temperature"] = constants.DEFAULT_TEMPERATURE
    return chatbot


def delete_chatbot_service(chatbot_id: str):
    """Service logic for deleting a chatbot."""
    from .agent_service import clear_agent_cache
    get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()
    db.delete_chatbot(chatbot_id)
    clear_agent_cache(chatbot_id)
    return {"message": "Chatbot deleted successfully", "chatbot_id": chatbot_id}


def create_schema_extractor(db_url, db_type, credentials_json=None, schema_name=None, selected_tables=None):
    """Create SchemaExtractor instance with proper credentials"""
    if db_type == "bigquery" and credentials_json:
        return SchemaExtractor(db_url, db_type, credentials_json, schema_name=schema_name, selected_tables=selected_tables)
    else:
        return SchemaExtractor(db_url, db_type, schema_name=schema_name, selected_tables=selected_tables)


def extract_and_convert_schema(db_url, db_type, chatbot_id, credentials_json=None, schema_name=None, selected_tables=None):
    """Extract raw schema and convert to semantic model"""
    # Extract raw schema (timed)
    t_extract_start = time.time()
    schema_extractor = create_schema_extractor(
        db_url, db_type, credentials_json, schema_name=schema_name, selected_tables=selected_tables)
    raw_schema = schema_extractor.extract_schema()
    t_extract_end = time.time()
    logger.info(
        f"Schema extraction completed in {(t_extract_end - t_extract_start):.2f}s for {db_type} (schema={schema_name})")

    # Convert to semantic model (timed)
    t_convert_start = time.time()
    semantic_schema = convert_raw_schema_to_semantic(
        raw_schema=raw_schema,
        chatbot_id=chatbot_id,
        db_url=db_url,
        db_type=db_type
    )
    t_convert_end = time.time()
    logger.info(
        f"Semantic conversion completed in {(t_convert_end - t_convert_start):.2f}s; total tables={raw_schema.get('total_tables')}, total_columns={raw_schema.get('total_columns')}")

    return semantic_schema


def configure_database_service(chatbot_id: str):
    """Service logic for configuring a database. Parses request internally."""
    db = get_chatbot_db()
    
    try:
        db_config = api_schemas.DBConfigSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id)
    if chatbot.get("db_url"):
        raise ServiceException(
            "Database is already configured for this chatbot.", 409)

    db_type, db_name = db_config['db_type'], db_config['db_name']
    db_url, credentials_json = "", None

    if db_type == "postgresql":
        required = ["username", "password", "host", "port"]
        if not all(k in db_config for k in required):
            raise ServiceException(
                f"Missing required PostgreSQL fields: {required}", 400)
        u = quote_plus(str(db_config['username']))
        p = quote_plus(str(db_config['password']))
        db_url = f"postgresql+psycopg2://{u}:{p}@{db_config['host']}:{db_config['port']}/{db_name}"
    elif db_type == "sqlite":
        db_url = f"sqlite:///{db_name}.db"
    elif db_type == "bigquery":
        required = ["project_id", "dataset_id", "credentials_json"]
        if not all(k in db_config for k in required):
            raise ServiceException(
                f"Missing required BigQuery fields: {required}", 400)
        db_url = f"bigquery://{db_config['project_id']}/{db_config['dataset_id']}"
        credentials_json = db_config.get('credentials_json')
    elif db_type == "mysql":
        required = ["username", "password", "host", "port"]
        if not all(k in db_config for k in required):
            raise ServiceException(
                f"Missing required MySQL fields: {required}", 400)
        # Uses PyMySQL driver
        u = quote_plus(str(db_config['username']))
        p = quote_plus(str(db_config['password']))
        db_url = f"mysql+pymysql://{u}:{p}@{db_config['host']}:{db_config['port']}/{db_name}"
    elif db_type == "mssql":
        required = ["username", "password", "host", "port"]
        if not all(k in db_config for k in required):
            raise ServiceException(
                f"Missing required MSSQL fields: {required}", 400)
        driver = db_config.get('driver', 'ODBC Driver 18 for SQL Server')
        # URL encode spaces in driver
        driver_q = driver.replace(' ', '+')
        params = "Encrypt=yes&TrustServerCertificate=yes"
        u = quote_plus(str(db_config['username']))
        p = quote_plus(str(db_config['password']))
        db_url = (
            f"mssql+pyodbc://{u}:{p}@"
            f"{db_config['host']}:{db_config['port']}/{db_name}?driver={driver_q}&{params}"
        )

    tester = None
    t_connect_start = time.time()
    try:
        tester = AppDbUtil(db_url, credentials_json=credentials_json)
        conn = tester.db_engine.connect()
        conn.close()
    except Exception as e:
        raise ServiceException(f"Failed to connect to the database: {e}", 400)
    finally:
        if tester:
            tester.db_engine.dispose()
    t_connect_end = time.time()
    logger.info(f"DB connection test successful in {(t_connect_end - t_connect_start):.2f}s for {db_type}")

    try:
        semantic_schema = extract_and_convert_schema(
            db_url, db_type, chatbot_id, credentials_json, schema_name=db_config.get('schema_name'), selected_tables=db_config.get('selected_tables'))

        # Convert to JSON and store in chatbots table using clean structure
        import json
        semantic_schema_json = json.dumps(semantic_schema.to_json_dict())
        db.store_semantic_schema(chatbot_id, semantic_schema_json)

        # Build and store knowledge hashmap immediately after storing schema
        try:
            from .knowledge_cache_service import build_and_store_knowledge_cache
            build_and_store_knowledge_cache(chatbot_id)
        except Exception as cache_error:
            logger.error(f"Failed to build knowledge cache during DB config for chatbot {chatbot_id}: {cache_error}")

        schema_message = "Schema extracted and semantic model created successfully"

    except Exception as schema_error:
        # Log the error but don't fail the database configuration
        logging.error(
            f"Failed to extract schema for chatbot {chatbot_id}: {str(schema_error)}")
        schema_message = "Database configured but schema extraction failed"

    
    # Store selected_tables as JSON string
    selected_tables_json = None
    if db_config.get('selected_tables'):
        import json
        selected_tables_json = json.dumps(db_config.get('selected_tables'))
    
    update_params = {
        "chatbot_id": chatbot_id,
        "db_type": db_type,
        "db_url": db_url,
        "schema_name": db_config.get('schema_name'),
        "selected_tables": selected_tables_json,
        # After successfully configuring the application database we should mark the
        # chatbot as DB_CONFIGURED (not LLM_CONFIGURED). This ensures status ordering
        # checks that rely on ChatbotStatus behave correctly.
        "status": ChatbotStatus.DB_CONFIGURED.value,
        "credentials_json": credentials_json
    }
    return db.update_chatbot(**{k: v for k, v in update_params.items() if v is not None})


def get_schema_service(chatbot_id: str):
    """
    Service logic for extracting the raw database schema for a chatbot.
    """
    try:
        logger.info(f"Schema request for chatbot: {chatbot_id}")
        chatbot = get_chatbot_with_validation(chatbot_id)
        logger.info(f"Chatbot found: {chatbot.get('name')}")
       
        db_url = chatbot.get("db_url")
        if not db_url:
            logger.warning(f"No database URL configured for chatbot {chatbot_id}")
            raise ServiceException("Database not configured for this chatbot", 400)
       
        db_type = chatbot.get("db_type", "sqlite")
        credentials_json = chatbot.get("credentials_json")
       
        logger.info(f"Database URL: {db_url}")
        logger.info(f"Database type: {db_type}")
        logger.info(f"Schema name: {chatbot.get('schema_name')}")
        logger.info(f"Selected tables (raw): {chatbot.get('selected_tables')}")
        logger.info(f"Selected tables type: {type(chatbot.get('selected_tables'))}")
        logger.info(f"Chatbot keys: {list(chatbot.keys())}")
       
        # Extract schema directly
        logger.info("Extracting schema...")
        try:
            # Parse selected_tables from JSON string if available
            selected_tables = None
            logger.info(f"Checking selected_tables: {chatbot.get('selected_tables')}")
            if chatbot.get("selected_tables"):
                try:
                    import json
                    selected_tables = json.loads(chatbot.get("selected_tables"))
                    logger.info(f"[SUCCESS] Parsed selected_tables: {selected_tables}")
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[ERROR] Failed to parse selected_tables: {e}")
                    selected_tables = None
            else:
                logger.warning(f"[ERROR] No selected_tables found in chatbot data")
            
            # The SchemaExtractor should be used within a 'with' statement if possible,
            # but since it has a __del__ method, this is also safe.
            schema_extractor = SchemaExtractor(
                db_url, db_type, credentials_json,
                schema_name=chatbot.get("schema_name"),
                selected_tables=selected_tables
            )
            logger.info("Schema extractor created successfully")
           
            schema_info = schema_extractor.extract_schema()
            logger.info(f"Schema extracted: {len(schema_info.get('tables', []))} tables found")
           
            schema_summary = schema_extractor.get_schema_summary()
            logger.info(f"Schema summary generated: {len(schema_summary)} characters")
           
            # The service returns a clean Python dictionary
            return {
                "chatbot_id": chatbot_id,
                "schema": schema_info,
                "schema_summary": schema_summary,
                "database_type": db_type,
                "database_url": db_url
            }
        except Exception as e:
            logger.error(f"Schema extraction error for chatbot {chatbot_id}: {e}", exc_info=True)
            raise ServiceException(f"Failed to extract schema: {str(e)}", 500)
           
    except ServiceException:
        # Re-raise known exceptions to be handled by the global handler
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_raw_schema_service for chatbot {chatbot_id}: {e}", exc_info=True)
        raise ServiceException(str(e), 500)


def set_chatbot_ready_service(chatbot_id: str):
    """Service logic for finalizing chatbot setup. Parses request internally."""
    from .agent_service import get_agent, clear_agent_cache

    try:
        validated_data = api_schemas.ReadySchema().load(
            request.get_json(silent=True) or {})
        preview_content = validated_data.get('preview_content')
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    chatbot = get_chatbot_with_validation(chatbot_id)
    validate_chatbot_status(chatbot, "llm_configured")

    db, app_db = get_chatbot_db(), None
    try:
        app_db = AppDbUtil(
            chatbot['db_url'], credentials_json=chatbot.get('credentials_json'))
        enhanced_prompt = db.generate_enhanced_prompt(
            chatbot_id, app_db, preview_content=preview_content)
        db.create_chatbot_prompt(chatbot_id, enhanced_prompt)
    except Exception as e:
        raise ServiceException(f"Failed to generate enhanced prompt: {e}", 500)
    finally:
        if app_db:
            app_db.db_engine.dispose()

    db.update_chatbot(chatbot_id=chatbot_id, status=ChatbotStatus.READY.value)

    if not db.get_conversation_by_name(chatbot_id, constants.BENCHMARK_CONVERSATION_NAME):
        db.create_conversation(
            chatbot_id,
            constants.BENCHMARK_CONVERSATION_NAME,
            "active",
            constants.BENCHMARK_CONVERSATION_OWNER,
            conversationType="PINNED"
        )

    clear_agent_cache(chatbot_id)
    get_agent(chatbot_id)
    return {"status": ChatbotStatus.READY.value, "enhanced_prompt_generated": True}


def update_knowledge_base_service(chatbot_id: str):
    """Service logic for updating knowledge base settings. Parses request internally."""
    try:
        validated_data = api_schemas.KnowledgeBaseSchema().load(request.get_json())
    except ValidationError as err:
        raise ServiceException(f"Invalid request body: {err.messages}", 400)

    get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()
    update_args = dict(validated_data.items())
    return db.update_chatbot(chatbot_id=chatbot_id, **update_args)


def update_database_schema_service(chatbot_id: str):
    """Service for schema updates, clears cache."""
    get_chatbot_with_validation(chatbot_id)
    db = get_chatbot_db()
    db.clear_schema_cache(chatbot_id)

    time.sleep(1)

    return {
        "message": "Database schema cache cleared. Schema will be re-fetched on next request.",
        "chatbot_id": chatbot_id, "timestamp": time.time(), "status": "success"
    }


def test_database_connection_service():
    """
    Builds a connection string and attempts to connect to a database.
    Parses the request body internally to get connection data.
    """
    # 1. Validation and Parsing
    try:
        connection_data = api_schemas.ConnectionTestSchema().load(request.get_json())
    except ValidationError as err:
        # Raise a ServiceException for validation errors
        raise ServiceException(f"Validation failed: {err.messages}", 400)
    except Exception:
        raise ServiceException("Request body must be valid JSON.", 400)

    db_type = connection_data.get("db_type")
    db_name = connection_data.get("db_name")
    db_url = ""
    credentials_json = None

    # 2. Build the connection URL
    if db_type == "postgresql":
        required = ["username", "password", "host", "port"]
        if not all(k in connection_data for k in required):
            raise ServiceException(
                "Missing required PostgreSQL fields: username, password, host, port", 400)
        u = quote_plus(str(connection_data['username']))
        p = quote_plus(str(connection_data['password']))
        db_url = f"postgresql+psycopg2://{u}:{p}@{connection_data['host']}:{connection_data['port']}/{db_name}"
    elif db_type == "sqlite":
        db_url = f"sqlite:///{db_name}.db"
    elif db_type == "bigquery":
        required = ["project_id", "dataset_id", "credentials_json"]
        if not all(k in connection_data for k in required):
            raise ServiceException(
                "Missing required BigQuery fields: project_id, dataset_id, credentials_json", 400)
        db_url = f"bigquery://{connection_data['project_id']}/{connection_data['dataset_id']}"
        credentials_json = connection_data.get('credentials_json')
    elif db_type == "mysql":
        required = ["username", "password", "host", "port"]
        if not all(k in connection_data for k in required):
            raise ServiceException(
                "Missing required MySQL fields: username, password, host, port", 400)
        u = quote_plus(str(connection_data['username']))
        p = quote_plus(str(connection_data['password']))
        db_url = f"mysql+pymysql://{u}:{p}@{connection_data['host']}:{connection_data['port']}/{db_name}"
    elif db_type == "mssql":
        required = ["username", "password", "host", "port"]
        if not all(k in connection_data for k in required):
            raise ServiceException(
                "Missing required MSSQL fields: username, password, host, port", 400)
        driver = connection_data.get('driver', 'ODBC Driver 18 for SQL Server')
        driver_q = driver.replace(' ', '+')
        params = "Encrypt=yes&TrustServerCertificate=yes"
        u = quote_plus(str(connection_data['username']))
        p = quote_plus(str(connection_data['password']))
        db_url = (
            f"mssql+pyodbc://{u}:{p}@"
            f"{connection_data['host']}:{connection_data['port']}/{db_name}?driver={driver_q}&{params}"
        )
    else:
        raise ServiceException(f"Unsupported db_type: {db_type}", 400)

    # 3. Attempt to connect
    tester = None
    try:
        tester = AppDbUtil(db_url, credentials_json=credentials_json)
        tables = []
        conn = tester.db_engine.connect()

        # Enumerate schemas for user selection; exclude system schemas
        from sqlalchemy import inspect
        insp = inspect(tester.db_engine)
        try:
            all_schemas = insp.get_schema_names()
        except Exception:
            all_schemas = []

        # Fallbacks per engine if inspector returns empty
        try:
            if not all_schemas:
                dialect = tester.db_engine.dialect.name.lower()
                if dialect == "mssql":
                    rs = conn.exec_driver_sql("SELECT name FROM sys.schemas")
                    all_schemas = [r[0] for r in rs]
                elif dialect == "postgresql":
                    rs = conn.exec_driver_sql("SELECT schema_name FROM information_schema.schemata")
                    all_schemas = [r[0] for r in rs]
                elif dialect == "mysql":
                    rs = conn.exec_driver_sql("SELECT schema_name FROM information_schema.schemata")
                    all_schemas = [r[0] for r in rs]
        except Exception:
            pass

        # Normalize and filter system schemas across engines
        system_like = {"SYS", "INFORMATION_SCHEMA", "PG_CATALOG", "PG_TOAST"}
        schemas = [s for s in (all_schemas or []) if s and s.upper() not in system_like]

        # If a specific schema_name was provided in the request, attempt to list tables for it
        schema_name_requested = connection_data.get('schema_name')
        if schema_name_requested:
            try:
                # Use SQLAlchemy inspector to get table names for the schema
                try:
                    tables = insp.get_table_names(schema=schema_name_requested)
                except Exception:
                    # Fallback raw queries per dialect
                    dialect = tester.db_engine.dialect.name.lower()
                    if dialect == 'mssql':
                        rs = conn.exec_driver_sql(
                            "SELECT t.name FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE s.name = :schema",
                            {'schema': schema_name_requested}
                        )
                        tables = [r[0] for r in rs]
                    elif dialect in ('postgresql', 'mysql'):
                        rs = conn.exec_driver_sql(
                            "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema",
                            {'schema': schema_name_requested}
                        )
                        tables = [r[0] for r in rs]
            except Exception:
                tables = []

        conn.close()
        return {"success": True, "message": f"{db_type.title()} database connection test successful.", "schemas": schemas, "tables": tables}
    except Exception as e:
        logging.error(f"Database connection test failed for {db_type}: {e}")
        raise ServiceException(f"Failed to connect to database: {str(e)}", 400)
    finally:
        if tester and getattr(tester, 'db_engine', None):
            try:
                tester.db_engine.dispose()
            except Exception:
                pass


def get_semantic_schema_service(chatbot_id: str):
    """
    Service logic for retrieving and parsing the semantic schema for a chatbot.
    """
    get_chatbot_with_validation(chatbot_id)  # Validate chatbot exists
    db = get_chatbot_db()

    semantic_schema_json = db.get_semantic_schema(chatbot_id)

    if not semantic_schema_json:
        raise ServiceException(
            "No semantic schema found for this chatbot", 404)
    
    # 🔍 DEBUG: Log the raw JSON to see what's being loaded
    print(f"🔍 RAW SCHEMA JSON: {semantic_schema_json[:500]}...")
    print(f"🔍 SCHEMA JSON LENGTH: {len(semantic_schema_json)}")

    try:
        # Parse the JSON string first, then validate with Pydantic
        import json
        semantic_schema_data = json.loads(semantic_schema_json)
        
        # 🔍 DEBUG: Check what priority fields are in the loaded schema
        print("🔍 LOADED SCHEMA DEBUG: Checking loaded schema for priority fields...")
        for table_name, table_data in semantic_schema_data.get('tables', {}).items():
            if isinstance(table_data, dict) and 'columns' in table_data:
                for col_name, col_data in table_data['columns'].items():
                    if isinstance(col_data, dict):
                        priority_fields = {
                            'priority': col_data.get('priority'),
                            'description': col_data.get('description'),
                            'business_context': col_data.get('business_context'),
                            'business_terms': col_data.get('business_terms'),
                            'is_preferred': col_data.get('is_preferred'),
                            'use_cases': col_data.get('use_cases'),
                            'relevance_keywords': col_data.get('relevance_keywords')
                        }
                        # Only log if any priority fields are present
                        if any(priority_fields.values()):
                            print(f"🔍 LOADED PRIORITY FIELDS: {table_name}.{col_name}: {priority_fields}")

        # ---------------- Normalization for legacy/new mixed schemas ---------------- #
        def _normalize_inbound_schema(data: dict) -> dict:
            try:
                # ------- Database-level metrics: accept strings or loose objects -------
                db_metrics = data.get("metrics")
                print(f"DEBUG: Received database metrics: {db_metrics} (type: {type(db_metrics)})")
                norm_db_metrics = []
                if isinstance(db_metrics, list):
                    iterable = db_metrics
                elif isinstance(db_metrics, (str, dict)):
                    iterable = [db_metrics]
                else:
                    iterable = []

                for m in iterable:
                    if isinstance(m, str):
                        norm_db_metrics.append({
                            "name": m,
                            "expression": "COUNT(*)",
                            "default_filters": []
                        })
                    elif isinstance(m, dict):
                        name = m.get("name") or m.get("metric") or m.get("id") or "metric"
                        expr = m.get("expression") or m.get("value") or "COUNT(*)"
                        norm_db_metrics.append({
                            "name": name,
                            "expression": expr,
                            "default_filters": m.get("default_filters", [])
                        })
                data["metrics"] = norm_db_metrics
                print(f"DEBUG: Normalized database metrics: {norm_db_metrics}")

                tables = data.get("tables", {}) or {}
                for t_name, t in list(tables.items()):
                    # Ensure metrics shape is dict for tables
                    table_metrics = t.get("metrics", {})
                    print(f"DEBUG: Table {t_name} metrics received: {table_metrics}")
                    
                    if isinstance(table_metrics, list):
                        # convert ["metric_a"] -> {"metric_a": { name, expression, default_filters }}
                        mobj = {}
                        for m in table_metrics:
                            if isinstance(m, str):
                                mobj[m] = {
                                    "name": m,
                                    "expression": "COUNT(*)",
                                    "default_filters": []
                                }
                        t["metrics"] = mobj
                        print(f"DEBUG: Table {t_name} metrics normalized from list: {mobj}")
                    elif isinstance(table_metrics, dict):
                        print(f"DEBUG: Table {t_name} metrics already in dict format: {table_metrics}")
                    else:
                        print(f"DEBUG: Table {t_name} metrics in unexpected format: {type(table_metrics)}")

                    # Table synonyms: accept strings or dicts
                    table_syns = t.get("synonyms", []) or []
                    print(f"DEBUG: Table {t_name} synonyms received: {table_syns}")
                    norm_table_syns = []
                    for s in table_syns:
                        if isinstance(s, str):
                            norm_table_syns.append({"synonym": s, "sample_values": []})
                        elif isinstance(s, dict):
                            norm_table_syns.append({
                                "synonym": s.get("synonym", ""),
                                "sample_values": s.get("sample_values", [])
                            })
                    t["synonyms"] = norm_table_syns
                    print(f"DEBUG: Table {t_name} synonyms normalized: {norm_table_syns}")

                    cols = t.get("columns", {}) or {}
                    for c_name, c in list(cols.items()):
                        # Debug: Check business_context field
                        if c_name in ['AdditionalPaymentID', 'VendorNumber', 'VendorName']:
                            print(f"DEBUG: Column {t_name}.{c_name} business_context before normalization: {c.get('business_context')}")
                        
                        # fk may be boolean; model expects object or None
                        if isinstance(c.get("fk"), bool):
                            if c.get("fk") and isinstance(c.get("fk_ref"), dict):
                                c["fk"] = {
                                    "table": c["fk_ref"].get("table", ""),
                                    "column": c["fk_ref"].get("column", "")
                                }
                            else:
                                # set to None to satisfy Optional[ForeignKeyReference]
                                c["fk"] = None
                        # column synonyms: accept strings or dicts
                        syns = c.get("synonyms", []) or []
                        print(f"DEBUG: Column {t_name}.{c_name} synonyms received: {syns}")
                        norm_syns = []
                        for s in syns:
                            if isinstance(s, str):
                                norm_syns.append({"synonym": s, "sample_values": []})
                            elif isinstance(s, dict):
                                norm_syns.append({
                                    "synonym": s.get("synonym", ""),
                                    "sample_values": s.get("sample_values", [])
                                })
                        c["synonyms"] = norm_syns
                        print(f"DEBUG: Column {t_name}.{c_name} synonyms normalized: {norm_syns}")
                        
                        # Debug: Check business_context field after normalization
                        if c_name in ['AdditionalPaymentID', 'VendorNumber', 'VendorName']:
                            print(f"DEBUG: Column {t_name}.{c_name} business_context after normalization: {c.get('business_context')}")

                # Relationships: ensure synonyms are strings
                rels = data.get("relationships", []) or []
                for i, r in enumerate(rels):
                    rel_syns = r.get("synonyms", [])
                    print(f"DEBUG: Relationship {i} synonyms received: {rel_syns}")
                    if isinstance(rel_syns, list):
                        normalized_rel_syns = [
                            (s.get("synonym") if isinstance(s, dict) else str(s))
                            for s in rel_syns
                        ]
                        r["synonyms"] = normalized_rel_syns
                        print(f"DEBUG: Relationship {i} synonyms normalized: {normalized_rel_syns}")
                return data
            except Exception:
                return data

        semantic_schema_data = _normalize_inbound_schema(semantic_schema_data)
        
        # Pydantic model validation happens here in the service layer
        try:
            semantic_schema = DatabaseSchema.model_validate(semantic_schema_data)
            print(f"DEBUG: Pydantic validation successful")
        except Exception as validation_error:
            print(f"DEBUG: Pydantic validation failed: {validation_error}")
            print(f"DEBUG: Data being validated: {semantic_schema_data}")
            raise validation_error

        # Return the parsed data as a dictionary using the clean structure
        result = semantic_schema.to_json_dict()
        
        return result

    except json.JSONDecodeError as json_error:
        logger.error(
            f"Failed to parse JSON for chatbot {chatbot_id}: {str(json_error)}", exc_info=True)
        raise ServiceException("Invalid JSON format in stored semantic schema", 500)
    except Exception as parse_error:
        logger.error(
            f"Failed to parse semantic schema for chatbot {chatbot_id}: {str(parse_error)}", exc_info=True)
        raise ServiceException("Failed to parse stored semantic schema", 500)


def update_semantic_schema_service(chatbot_id: str):
    """
    Service logic for validating and updating the semantic schema for a chatbot.
    Parses the request internally.
    """
    get_chatbot_with_validation(chatbot_id)  # Validate chatbot exists

    if not request.is_json:
        raise ServiceException("Request body must be JSON", 400)

    data = request.get_json()
    semantic_schema_data = data.get("semantic_schema")

    if not semantic_schema_data:
        raise ServiceException(
            "A 'semantic_schema' object is required in the request body", 400)

    # 🔍 LOGGING: Track schema updates
    print(f"UPDATE SEMANTIC SCHEMA: Updating schema for chatbot {chatbot_id}")
    print(f"Schema keys: {list(semantic_schema_data.keys()) if isinstance(semantic_schema_data, dict) else 'Not a dict'}")
    print(f"Tables: {len(semantic_schema_data.get('tables', {}))}")
    print(f"Metrics: {len(semantic_schema_data.get('metrics', []))}")
    print(f"Metrics data: {semantic_schema_data.get('metrics', [])}")
    
    # 🔍 LOG PRIORITY FIELDS: Check for priority fields in incoming schema
    print("🔍 PRIORITY FIELDS DEBUG: Checking incoming schema for priority fields...")
    print(f"🔍 SCHEMA KEYS: {list(semantic_schema_data.keys())}")
    print(f"🔍 TABLES COUNT: {len(semantic_schema_data.get('tables', {}))}")
    
    priority_fields_found = False
    for table_name, table_data in semantic_schema_data.get('tables', {}).items():
        if isinstance(table_data, dict) and 'columns' in table_data:
            print(f"🔍 TABLE {table_name}: {len(table_data['columns'])} columns")
            for col_name, col_data in table_data['columns'].items():
                if isinstance(col_data, dict):
                    priority_fields = {
                        'priority': col_data.get('priority'),
                        'description': col_data.get('description'),
                        'business_context': col_data.get('business_context'),
                        'business_terms': col_data.get('business_terms'),
                        'is_preferred': col_data.get('is_preferred'),
                        'use_cases': col_data.get('use_cases'),
                        'relevance_keywords': col_data.get('relevance_keywords')
                    }
                    # Only log if any priority fields are present
                    if any(priority_fields.values()):
                        print(f"🔍 PRIORITY FIELDS: {table_name}.{col_name}: {priority_fields}")
                        priority_fields_found = True
    
    if not priority_fields_found:
        print("🔍 NO PRIORITY FIELDS FOUND IN INCOMING SCHEMA!")
        print("🔍 This means the frontend is not sending priority fields")
        
        # Show sample column data to debug
        for table_name, table_data in semantic_schema_data.get('tables', {}).items():
            if isinstance(table_data, dict) and 'columns' in table_data:
                sample_col = list(table_data['columns'].items())[0] if table_data['columns'] else None
                if sample_col:
                    col_name, col_data = sample_col
                    print(f"🔍 SAMPLE COLUMN {table_name}.{col_name}: {list(col_data.keys())}")
                    break
    
    # Log business metrics being updated
    for metric in semantic_schema_data.get('metrics', []):
        print(f"  Metric: {metric.get('name', 'Unknown')} = {metric.get('expression', 'No expression')}")
    
    # Log tables with business context
    for table_name, table_data in semantic_schema_data.get('tables', {}).items():
        if table_data.get('business_context'):
            print(f"  Table {table_name}: {table_data.get('business_context')}")
        
        # Log columns with business context
        for col_name, col_data in table_data.get('columns', {}).items():
            if col_data.get('business_context'):
                print(f"  Column {table_name}.{col_name}: {col_data.get('business_context')}")
    
    print(f"{'='*80}\n")
    
    # Validate the incoming schema data using the Pydantic model
    try:
        logger.info(f"Validating semantic schema for chatbot {chatbot_id}")
        logger.info(f"Schema data keys: {list(semantic_schema_data.keys()) if isinstance(semantic_schema_data, dict) else 'Not a dict'}")
        
        # ---------------- Normalization for inbound payload (same rules as GET) ---------------- #
        def _normalize_inbound_schema(data: dict) -> dict:
            try:
                tables = data.get("tables", {}) or {}
                for t_name, t in list(tables.items()):
                    # Ensure metrics shape is dict for tables
                    if isinstance(t.get("metrics"), list):
                        mobj = {}
                        for m in t.get("metrics", []):
                            if isinstance(m, str):
                                mobj[m] = {
                                    "name": m,
                                    "expression": "COUNT(*)",
                                    "default_filters": []
                                }
                        t["metrics"] = mobj

                    cols = t.get("columns", {}) or {}
                    for c_name, c in list(cols.items()):
                        # fk may be boolean; model expects object or None
                        if isinstance(c.get("fk"), bool):
                            if c.get("fk") and isinstance(c.get("fk_ref"), dict):
                                c["fk"] = {
                                    "table": c["fk_ref"].get("table", ""),
                                    "column": c["fk_ref"].get("column", "")
                                }
                            else:
                                c["fk"] = None
                        # Normalize column synonyms to objects
                        syns = c.get("synonyms", []) or []
                        norm_syns = []
                        for s in syns:
                            if isinstance(s, str):
                                norm_syns.append({"synonym": s, "sample_values": []})
                            elif isinstance(s, dict):
                                norm_syns.append({
                                    "synonym": s.get("synonym", ""),
                                    "sample_values": s.get("sample_values", [])
                                })
                        c["synonyms"] = norm_syns

                # Relationships: ensure synonyms are strings
                rels = data.get("relationships", []) or []
                for r in rels:
                    if isinstance(r.get("synonyms"), list):
                        r["synonyms"] = [
                            (s.get("synonym") if isinstance(s, dict) else str(s))
                            for s in r.get("synonyms", [])
                        ]
                return data
            except Exception:
                return data

        semantic_schema_data = _normalize_inbound_schema(semantic_schema_data)

        # 🔍 DEBUG: Check what priority fields are in the data before validation
        print("🔍 PRE-VALIDATION DEBUG: Checking priority fields before Pydantic validation...")
        for table_name, table_data in semantic_schema_data.get('tables', {}).items():
            if isinstance(table_data, dict) and 'columns' in table_data:
                for col_name, col_data in table_data['columns'].items():
                    if isinstance(col_data, dict):
                        priority_fields = {
                            'priority': col_data.get('priority'),
                            'description': col_data.get('description'),
                            'business_context': col_data.get('business_context'),
                            'business_terms': col_data.get('business_terms'),
                            'is_preferred': col_data.get('is_preferred'),
                            'use_cases': col_data.get('use_cases'),
                            'relevance_keywords': col_data.get('relevance_keywords')
                        }
                        # Only log if any priority fields are present
                        if any(priority_fields.values()):
                            print(f"🔍 PRE-VALIDATION PRIORITY FIELDS: {table_name}.{col_name}: {priority_fields}")
        
        semantic_schema = DatabaseSchema.model_validate(semantic_schema_data)
        logger.info(f"Schema validation successful for chatbot {chatbot_id}")
        
        # 🔍 DEBUG: Check what priority fields are in the validated model
        print("🔍 POST-VALIDATION DEBUG: Checking priority fields after Pydantic validation...")
        for table_name, table_data in semantic_schema.tables.items():
            for col_name, col_data in table_data.columns.items():
                priority_fields = {
                    'priority': getattr(col_data, 'priority', None),
                    'description': getattr(col_data, 'description', None),
                    'business_context': getattr(col_data, 'business_context', None),
                    'business_terms': getattr(col_data, 'business_terms', None),
                    'is_preferred': getattr(col_data, 'is_preferred', None),
                    'use_cases': getattr(col_data, 'use_cases', None),
                    'relevance_keywords': getattr(col_data, 'relevance_keywords', None)
                }
                # Only log if any priority fields are present
                if any(priority_fields.values()):
                    print(f"🔍 POST-VALIDATION PRIORITY FIELDS: {table_name}.{col_name}: {priority_fields}")
        
        # Enforce business rule: the schema's ID must match the chatbot's ID
        if semantic_schema.id != chatbot_id:
            raise ServiceException(
                "The id in the schema does not match the chatbot's ID", 400)

    except Exception as validation_error:
        # Catches Pydantic validation errors and other issues
        logger.error(f"Schema validation failed for chatbot {chatbot_id}: {str(validation_error)}")
        raise ServiceException(
            f"Invalid semantic schema format: {str(validation_error)}", 400)

    db = get_chatbot_db()

    # Convert the validated Pydantic model back to a JSON string for storage using clean structure
    try:
        logger.info(f"Converting schema to JSON for chatbot {chatbot_id}")
        schema_dict = semantic_schema.to_json_dict()
        logger.info(f"Schema dict keys: {list(schema_dict.keys()) if isinstance(schema_dict, dict) else 'Not a dict'}")
        
        semantic_schema_json = json.dumps(schema_dict)
        logger.info(f"JSON serialization successful, size: {len(semantic_schema_json)} characters")
        
    except Exception as json_error:
        logger.error(f"JSON serialization failed for chatbot {chatbot_id}: {str(json_error)}")
        raise ServiceException(f"Failed to serialize schema to JSON: {str(json_error)}", 500)
    
    try:
        logger.info(f"Storing semantic schema in database for chatbot {chatbot_id}")
        success = db.store_semantic_schema(chatbot_id, semantic_schema_json)
        logger.info(f"Database storage result: {success}")
        
        # 🔍 LOGGING: Track database storage result
        if success:
            print(f"✅ Schema successfully updated in database for chatbot {chatbot_id}")
            
            # 🔍 LOG PRIORITY FIELDS: Verify what was actually stored
            print("🔍 PRIORITY FIELDS DEBUG: Verifying stored schema contains priority fields...")
            try:
                stored_schema = json.loads(semantic_schema_json)
                for table_name, table_data in stored_schema.get('tables', {}).items():
                    if isinstance(table_data, dict) and 'columns' in table_data:
                        for col_name, col_data in table_data['columns'].items():
                            if isinstance(col_data, dict):
                                priority_fields = {
                                    'priority': col_data.get('priority'),
                                    'description': col_data.get('description'),
                                    'business_context': col_data.get('business_context'),
                                    'business_terms': col_data.get('business_terms'),
                                    'is_preferred': col_data.get('is_preferred'),
                                    'use_cases': col_data.get('use_cases'),
                                    'relevance_keywords': col_data.get('relevance_keywords')
                                }
                                # Only log if any priority fields are present
                                if any(priority_fields.values()):
                                    print(f"🔍 STORED PRIORITY FIELDS: {table_name}.{col_name}: {priority_fields}")
            except Exception as e:
                print(f"🔍 ERROR: Could not verify stored priority fields: {e}")
        else:
            print(f"❌ Failed to update schema in database for chatbot {chatbot_id}")
        
        # Rebuild knowledge cache with updated schema
        if success:
            try:
                from .knowledge_cache_service import build_and_store_knowledge_cache
                logger.info(f"Rebuilding knowledge cache for chatbot {chatbot_id} after schema update")
                build_and_store_knowledge_cache(chatbot_id)
                logger.info(f"Knowledge cache rebuilt successfully for chatbot {chatbot_id}")
            except Exception as cache_error:
                logger.error(f"Failed to rebuild knowledge cache after schema update for chatbot {chatbot_id}: {cache_error}")
                # Don't fail the schema update if cache rebuild fails
        
    except Exception as db_error:
        logger.error(f"Database storage failed for chatbot {chatbot_id}: {str(db_error)}")
        raise ServiceException(f"Failed to store schema in database: {str(db_error)}", 500)

    if not success:
        logger.error(f"Database storage returned False for chatbot {chatbot_id}")
        raise ServiceException(
            "Failed to store semantic schema in the database", 500)

    return {"message": "Semantic schema updated successfully", "chatbot_id": chatbot_id}


def export_semantic_schema_service(chatbot_id: str):
    """
    Service logic for exporting the semantic schema for a chatbot as CSV.
    """
    get_chatbot_with_validation(chatbot_id)  # Validate chatbot exists
    db = get_chatbot_db()

    semantic_schema_json = db.get_semantic_schema(chatbot_id)

    if not semantic_schema_json:
        raise ServiceException(
            "No semantic schema found for this chatbot", 404)

    try:
        import json
        import csv
        import io
        from flask import Response
        
        semantic_schema_data = json.loads(semantic_schema_json)
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Table Name',
            'Column Name', 
            'Description',
            'Business Context',
            'Exclude Column',
            'Data Type',
            'Is Primary Key',
            'Is Foreign Key'
        ])
        
        # Write data rows
        tables = semantic_schema_data.get('tables', {})
        for table_id, table in tables.items():
            columns = table.get('columns', {})
            for column_id, column in columns.items():
                writer.writerow([
                    table.get('display_name', table_id),
                    column.get('display_name', column_id),
                    column.get('description', ''),
                    column.get('business_context', ''),
                    'Yes' if column.get('exclude_column', False) else 'No',
                    column.get('data_type', column.get('type', '')),
                    'Yes' if column.get('is_primary_key', column.get('pk', False)) else 'No',
                    'Yes' if column.get('is_foreign_key', column.get('fk', False)) else 'No'
                ])
        
        # Create response
        output.seek(0)
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=schema_{chatbot_id}_{semantic_schema_data.get("display_name", "export")}.csv'
            }
        )
        
    except json.JSONDecodeError as json_error:
        logger.error(f"Failed to parse JSON for chatbot {chatbot_id}: {str(json_error)}")
        raise ServiceException("Invalid JSON format in stored semantic schema", 500)
    except Exception as parse_error:
        logger.error(f"Failed to export semantic schema for chatbot {chatbot_id}: {str(parse_error)}")
        raise ServiceException("Failed to export semantic schema", 500)


def import_semantic_schema_service(chatbot_id: str):
    """
    Service logic for importing a semantic schema for a chatbot from CSV.
    """
    get_chatbot_with_validation(chatbot_id)  # Validate chatbot exists
    
    if not request.files:
        raise ServiceException("No file provided", 400)
    
    file = request.files.get('file')
    if not file:
        raise ServiceException("No file provided", 400)
    
    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise ServiceException("File must be CSV or Excel format", 400)
    
    try:
        import json
        import csv
        import io
        import pandas as pd
        
        # Read file content based on file type
        if file.filename.lower().endswith('.csv'):
            # Handle CSV files
            content = file.read().decode('utf-8')
            lines = content.split('\n')
            
            if len(lines) < 2:
                raise ServiceException("Invalid CSV format - must have header and data rows", 400)
            
            # Parse CSV
            reader = csv.reader(lines)
            headers = next(reader)
            rows = list(reader)
        else:
            # Handle Excel files using pandas
            try:
                # Reset file pointer
                file.seek(0)
                
                # Read Excel file
                if file.filename.lower().endswith('.xlsx'):
                    df = pd.read_excel(file, engine='openpyxl')
                elif file.filename.lower().endswith('.xls'):
                    df = pd.read_excel(file, engine='xlrd')
                else:
                    raise ServiceException("Unsupported file format", 400)
                
                if df.empty:
                    raise ServiceException("Excel file is empty", 400)
                
                # Convert to list format for processing
                headers = df.columns.tolist()
                rows = df.values.tolist()
                
                logger.info(f"Successfully read Excel file with {len(rows)} rows and {len(headers)} columns")
                
            except Exception as excel_error:
                logger.error(f"Error reading Excel file: {str(excel_error)}")
                raise ServiceException(f"Failed to read Excel file: {str(excel_error)}", 400)
        
        # Find column indices
        logger.info(f"Available columns in uploaded file: {headers}")
        
        table_name_idx = headers.index('Table Name') if 'Table Name' in headers else -1
        column_name_idx = headers.index('Column Name') if 'Column Name' in headers else -1
        description_idx = headers.index('Description') if 'Description' in headers else -1
        business_context_idx = headers.index('Business Context') if 'Business Context' in headers else -1
        exclude_column_idx = headers.index('Exclude Column') if 'Exclude Column' in headers else -1
        
        # Try alternative names for required columns first
        if table_name_idx == -1:
            # Try alternative names for table
            alt_table_names = ['table_name', 'Table', 'table', 'TABLE_NAME', 'TableName', 'table name']
            for alt_name in alt_table_names:
                if alt_name in headers:
                    table_name_idx = headers.index(alt_name)
                    logger.info(f"Found table column with alternative name: {alt_name}")
                    break

        if column_name_idx == -1:
            # Try alternative names for column
            alt_column_names = ['column_name', 'Column', 'column', 'COLUMN_NAME', 'ColumnName', 'column name']
            for alt_name in alt_column_names:
                if alt_name in headers:
                    column_name_idx = headers.index(alt_name)
                    logger.info(f"Found column with alternative name: {alt_name}")
                    break
        
        # Try alternative names for optional columns
        if description_idx == -1:
            alt_desc_names = ['description', 'Description', 'DESCRIPTION', 'desc', 'Desc', 'description']
            for alt_name in alt_desc_names:
                if alt_name in headers:
                    description_idx = headers.index(alt_name)
                    logger.info(f"Found description column with alternative name: {alt_name}")
                    break

        if business_context_idx == -1:
            alt_bc_names = ['business_context', 'Business Context', 'BUSINESS_CONTEXT', 'business context', 'BusinessContext']
            for alt_name in alt_bc_names:
                if alt_name in headers:
                    business_context_idx = headers.index(alt_name)
                    logger.info(f"Found business context column with alternative name: {alt_name}")
                    break
        
        if exclude_column_idx == -1:
            alt_exclude_names = ['exclude_column', 'Exclude Column', 'EXCLUDE_COLUMN', 'exclude column', 'ExcludeColumn', 'exclude', 'Exclude']
            for alt_name in alt_exclude_names:
                if alt_name in headers:
                    exclude_column_idx = headers.index(alt_name)
                    logger.info(f"Found exclude column with alternative name: {alt_name}")
                    break
        
        if table_name_idx == -1 or column_name_idx == -1:
            error_msg = f"Required columns not found. Available columns: {headers}. "
            error_msg += f"Looking for 'Table Name' (found: {table_name_idx != -1}) and 'Column Name' (found: {column_name_idx != -1}). "
            error_msg += "Please ensure your file has columns named 'Table Name' and 'Column Name'. "
            error_msg += "You can export a schema first to see the expected format."
            logger.error(error_msg)
            raise ServiceException(error_msg, 400)
        
        # Get current schema
        db = get_chatbot_db()
        semantic_schema_json = db.get_semantic_schema(chatbot_id)
        
        if not semantic_schema_json:
            raise ServiceException("No semantic schema found for this chatbot", 404)
        
        semantic_schema_data = json.loads(semantic_schema_json)
        
        # Create mapping of imported data
        imported_data = {}
        
        logger.info(f"CSV Headers: {headers}")
        logger.info(f"Column indices - Table: {table_name_idx}, Column: {column_name_idx}, Description: {description_idx}, Business Context: {business_context_idx}, Exclude: {exclude_column_idx}")
        
        # Debug: Check if business context column was found
        if business_context_idx == -1:
            logger.warning("Business Context column not found in uploaded file")
            logger.warning(f"Available headers: {headers}")
        else:
            logger.info(f"Business Context column found at index {business_context_idx}: '{headers[business_context_idx]}'")
        
        for row_num, row in enumerate(rows, 1):
            if len(row) < max(table_name_idx, column_name_idx) + 1:
                logger.warning(f"Row {row_num} has insufficient columns, skipping")
                continue
                
            # Convert all values to strings and handle NaN values
            row = [str(cell) if pd.notna(cell) else '' for cell in row]
            
            table_name = row[table_name_idx].strip()
            column_name = row[column_name_idx].strip()
            description = row[description_idx].strip() if description_idx != -1 and len(row) > description_idx else ''
            business_context = row[business_context_idx].strip() if business_context_idx != -1 and len(row) > business_context_idx else ''
            exclude_column = row[exclude_column_idx].strip().lower() == 'yes' if exclude_column_idx != -1 and len(row) > exclude_column_idx else False
            
            if not table_name or not column_name:
                logger.warning(f"Row {row_num} has empty table or column name, skipping")
                continue
                
            if table_name not in imported_data:
                imported_data[table_name] = {}
            
            # Store description and business_context as requested
            imported_data[table_name][column_name] = {
                'description': description,
                'business_context': business_context,
                'exclude_column': exclude_column
            }
            
            logger.info(f"Row {row_num}: Table='{table_name}', Column='{column_name}', Description='{description}', Business Context='{business_context}', Exclude={exclude_column}")
            
            # Debug: Show raw business context value
            if business_context_idx != -1 and len(row) > business_context_idx:
                raw_business_context = row[business_context_idx] if business_context_idx < len(row) else 'N/A'
                logger.info(f"  Raw business context value: '{raw_business_context}' (type: {type(raw_business_context)})")
                logger.info(f"  Processed business context: '{business_context}' (empty: {not business_context})")
        
        logger.info(f"Imported data summary: {len(imported_data)} tables, {sum(len(cols) for cols in imported_data.values())} columns")
        
        # Debug: Log all imported data for verification
        for table_name, columns in imported_data.items():
            logger.info(f"Imported table '{table_name}' with columns:")
            for col_name, col_data in columns.items():
                logger.info(f"  - {col_name}: desc='{col_data['description']}', bc='{col_data['business_context']}', exclude={col_data['exclude_column']}")
        
        # Update schema with imported data
        tables = semantic_schema_data.get('tables', {})
        updated = False
        
        # Debug: Log available tables and columns
        logger.info(f"Available tables in schema: {list(tables.keys())}")
        for table_id, table in tables.items():
            logger.info(f"Table {table_id}: name='{table.get('name')}', display_name='{table.get('display_name')}'")
            columns = table.get('columns', {})
            logger.info(f"  Columns: {list(columns.keys())}")
            for col_id, col in columns.items():
                logger.info(f"    Column {col_id}: name='{col.get('name')}', display_name='{col.get('display_name')}'")
                # Check if business_context field exists in schema
                if 'business_context' in col:
                    logger.info(f"      business_context exists: '{col.get('business_context')}'")
                else:
                    logger.warning(f"      business_context field MISSING from schema for {col_id}")
        
        for table_name, columns in imported_data.items():
            # Find table by name - try multiple matching strategies
            table_entry = None
            for table_id, table in tables.items():
                # Try matching by display_name first, then name, then ID
                if (table.get('display_name') == table_name or 
                    table.get('name') == table_name or 
                    table_id == table_name):
                    table_entry = (table_id, table)
                    break
            
            if table_entry:
                table_id, table = table_entry
                table_columns = table.get('columns', {})
                
                # Update columns - try multiple matching strategies
                for column_name, column_data in columns.items():
                    column_entry = None
                    for col_id, col in table_columns.items():
                        # Try matching by display_name first, then name, then ID
                        if (col.get('display_name') == column_name or 
                            col.get('name') == column_name or 
                            col_id == column_name):
                            column_entry = (col_id, col)
                            break
                    
                    if column_entry:
                        col_id, col = column_entry
                        # Update the column with imported data
                        # Map description from Excel to description field in schema
                        if column_data['description']:
                            col['description'] = column_data['description']
                        
                        # Map business_context from Excel to business_context field in schema  
                        if column_data['business_context']:
                            col['business_context'] = column_data['business_context']
                        # Add exclude_column field
                        col['exclude_column'] = column_data['exclude_column']
                        updated = True
                        logger.info(f"Updated column {col_id} in table {table_id} with imported data:")
                        logger.info(f"  Description: '{column_data['description']}'")
                        logger.info(f"  Business Context: '{column_data['business_context']}'")
                        logger.info(f"  Exclude Column: {column_data['exclude_column']}")
                        
                        # Verify the field was actually set
                        logger.info(f"  VERIFICATION - Column {col_id} now has:")
                        logger.info(f"    description: '{col.get('description')}'")
                        logger.info(f"    business_context: '{col.get('business_context')}'")
                        logger.info(f"    exclude_column: {col.get('exclude_column')}")
                    else:
                        logger.warning(f"Could not find column '{column_name}' in table '{table_name}'")
            else:
                logger.warning(f"Could not find table '{table_name}' in schema")
        
        if updated:
            # Save updated schema
            updated_schema_json = json.dumps(semantic_schema_data)
            db.store_semantic_schema(chatbot_id, updated_schema_json)
            
            # Debug: Verify what was actually saved
            logger.info("Verifying saved schema contains description and business_context fields:")
            for table_id, table in semantic_schema_data.get('tables', {}).items():
                for col_id, col in table.get('columns', {}).items():
                    if col.get('description'):
                        logger.info(f"  {table_id}.{col_id}: description='{col.get('description')}'")
                    else:
                        logger.warning(f"  {table_id}.{col_id}: NO description field")
                    if col.get('business_context'):
                        logger.info(f"  {table_id}.{col_id}: business_context='{col.get('business_context')}'")
                    else:
                        logger.warning(f"  {table_id}.{col_id}: NO business_context field")
            
            # Debug: Check specifically for AdditionalPaymentID
            payments_table = semantic_schema_data.get('tables', {}).get('Payments', {})
            if payments_table:
                additional_payment_col = payments_table.get('columns', {}).get('AdditionalPaymentID', {})
                logger.info(f"AdditionalPaymentID column details: {additional_payment_col}")
                if additional_payment_col.get('description'):
                    logger.info(f"AdditionalPaymentID has description: '{additional_payment_col.get('description')}'")
                else:
                    logger.warning("AdditionalPaymentID does NOT have description field")
                if additional_payment_col.get('business_context'):
                    logger.info(f"AdditionalPaymentID has business_context: '{additional_payment_col.get('business_context')}'")
                else:
                    logger.warning("AdditionalPaymentID does NOT have business_context field")
            
            # Debug: Check a few random columns to see if description and business_context are present
            logger.info("Checking random columns for description and business_context:")
            for table_id, table in semantic_schema_data.get('tables', {}).items():
                columns = table.get('columns', {})
                sample_cols = list(columns.keys())[:3]  # Check first 3 columns
                for col_id in sample_cols:
                    col = columns[col_id]
                    if col.get('description'):
                        logger.info(f"  {table_id}.{col_id}: description='{col.get('description')}'")
                    else:
                        logger.warning(f"  {table_id}.{col_id}: NO description field")
                    if col.get('business_context'):
                        logger.info(f"  {table_id}.{col_id}: business_context='{col.get('business_context')}'")
                    else:
                        logger.warning(f"  {table_id}.{col_id}: NO business_context field")
                break  # Only check first table
            
            # Rebuild knowledge cache with updated schema
            try:
                from .knowledge_cache_service import build_and_store_knowledge_cache
                build_and_store_knowledge_cache(chatbot_id)
            except Exception as cache_error:
                logger.error(f"Failed to rebuild knowledge cache after schema import for chatbot {chatbot_id}: {cache_error}")
                # Don't fail the import if cache rebuild fails
        
        return {
            "message": "Semantic schema imported successfully", 
            "chatbot_id": chatbot_id,
            "updated_columns": len([col for cols in imported_data.values() for col in cols])
        }
        
    except Exception as import_error:
        logger.error(f"Failed to import semantic schema for chatbot {chatbot_id}: {str(import_error)}")
        raise ServiceException(f"Failed to import schema: {str(import_error)}", 500)
