import logging
from urllib.parse import quote_plus
import time
import json
from flask import app, current_app, request
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

        result.append({
            "chatbot_id": p["chatbot_id"],
            "name": p["name"],
            "status": p.get("status"),
            "created_at": created_at_iso,
            "llm_name": p.get("current_llm_name"),
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

    
    update_params = {
        "chatbot_id": chatbot_id,
        "db_type": db_type,
        "db_url": db_url,
        "schema_name": db_config.get('schema_name'),
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
       
        # Extract schema directly
        logger.info("Extracting schema...")
        try:
            # The SchemaExtractor should be used within a 'with' statement if possible,
            # but since it has a __del__ method, this is also safe.
            schema_extractor = SchemaExtractor(db_url, db_type, credentials_json)
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

    try:
        # Parse the JSON string first, then validate with Pydantic
        import json
        semantic_schema_data = json.loads(semantic_schema_json)

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
        return semantic_schema.to_json_dict()

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

        semantic_schema = DatabaseSchema.model_validate(semantic_schema_data)
        logger.info(f"Schema validation successful for chatbot {chatbot_id}")
        
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
