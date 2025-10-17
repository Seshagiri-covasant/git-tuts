import os
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, DateTime, ForeignKey, text, Boolean, func, desc, insert, select, literal, Float
from sqlalchemy import Text
from uuid import uuid4
from datetime import datetime
from sqlalchemy import Boolean, DateTime, func
import json
from sqlalchemy import inspect
import math
import logging
import time
from config import create_database_engine, get_chatbot_db_pool_config
import urllib.parse

# Configure logging for ChatbotDbUtil
chatbot_db_logger = logging.getLogger('chatbot_database')


class ChatbotDbUtil:
    def __init__(self, db_url=None, is_main_db=False):
        # Use PostgreSQL from environment if no db_url provided
        if db_url is None:
            db_user = os.getenv("DB_USER")
            raw_password = os.getenv("DB_PASSWORD")
            db_host = os.getenv("DB_HOST")
            db_port = os.getenv("DB_PORT")
            db_name = os.getenv("DB_NAME")
            encoded_password = urllib.parse.quote_plus(raw_password)
            db_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        if not db_url:
            raise ValueError("db_url must be provided")

        chatbot_db_logger.info(
            f"Initializing ChatbotDbUtil with db_url: {db_url}")

        # Use the new database configuration with proper connection pooling
        pool_config = get_chatbot_db_pool_config()
        self.db_engine = create_database_engine(db_url, pool_config)

        # Log connection pool status after initialization
        if hasattr(self.db_engine, 'pool'):
            chatbot_db_logger.info(
                f"Database engine initialized with pool size: {self.db_engine.pool.size()}")

        self.metadata = MetaData()
        self.chatbots_table = self.create_chatbots_table()
        # Semantic knowledge cache table (for storing cached semantic knowledge per chatbot)
        self.semantic_knowledge_cache_table = self.create_semantic_knowledge_cache_table()
        # API settings table (for storing global API settings)
        self.api_settings_table = self.create_api_settings_table()
        if not is_main_db:
            self.conversations_table = self.create_conversations_table()
            self.interactions_table = self.create_interactions_table()
            # Paged results storage for large SQL answers
            self.interaction_results_table = self.create_interaction_results_table()
            self.interaction_result_pages_table = self.create_interaction_result_pages_table()
            self.templates_table = self.create_templates_table()
            self.test_queries_table = self.create_test_queries_table()
            self.custom_tests_table = self.create_custom_tests_table()
            self.chatbot_prompt_table = self.create_chatbot_prompt_table()
        self.initialize_tables()

    def initialize_tables(self):
        """
        Creates all defined tables in the database if they don't exist.
        """
        try:
            # Create all tables in the database
            self.metadata.create_all(self.db_engine)
            # Migrate existing tables to add new columns if needed
            self.migrate_schema()
            print("DEBUG: Tables initialized successfully")
            return True
        except Exception as e:
            print(f"Error initializing tables: {e}")
            raise Exception(f"Failed to initialize tables: {e}")

    def migrate_schema(self):
        """
        Migrate existing database schema to add new columns if they don't exist.
        """
        try:
            inspector = inspect(self.db_engine)

            # Migrate chatbots table
            if inspector.has_table('chatbots'):
                existing_columns = [col['name']
                                    for col in inspector.get_columns('chatbots')]

                # Check for missing columns and add them
                missing_columns = []
                if 'industry' not in existing_columns:
                    missing_columns.append('industry')
                if 'vertical' not in existing_columns:
                    missing_columns.append('vertical')
                if 'domain' not in existing_columns:
                    missing_columns.append('domain')
                if 'knowledge_base_file' not in existing_columns:
                    missing_columns.append('knowledge_base_file')
                if 'credentials_json' not in existing_columns:
                    missing_columns.append('credentials_json')
                if 'semantic_schema_json' not in existing_columns:
                    missing_columns.append('semantic_schema_json')
                if 'llm_key_settings' not in existing_columns:
                    missing_columns.append('llm_key_settings')
                # New: persist selected DB schema name
                if 'schema_name' not in existing_columns:
                    missing_columns.append('schema_name')

                if missing_columns:
                    print(
                        f"DEBUG: Adding missing columns to chatbots table: {missing_columns}")
                    with self.db_engine.begin() as connection:
                        for column in missing_columns:
                            if column in ['industry', 'vertical', 'domain', 'knowledge_base_file', 'credentials_json', 'semantic_schema_json', 'llm_key_settings', 'schema_name']:
                                # Use TEXT for SQLite compatibility
                                connection.execute(
                                    text(f"ALTER TABLE chatbots ADD COLUMN {column} TEXT"))
                                print(
                                    f"DEBUG: Added column {column} to chatbots table")

            # Migrate api_settings table (create if it doesn't exist)
            if not inspector.has_table('api_settings'):
                print("DEBUG: Creating api_settings table")
                with self.db_engine.begin() as connection:
                    connection.execute(text("""
                        CREATE TABLE api_settings (
                            setting_key VARCHAR(100) PRIMARY KEY,
                            setting_value TEXT
                        )
                    """))
                    print("DEBUG: Created api_settings table")

            # Migrate interactions table (add ba_summary column if missing)
            if inspector.has_table('interactions'):
                existing_columns = [col['name'] for col in inspector.get_columns('interactions')]
                if 'ba_summary' not in existing_columns:
                    print("DEBUG: Adding missing column 'ba_summary' to interactions table")
                    with self.db_engine.begin() as connection:
                        connection.execute(text("ALTER TABLE interactions ADD COLUMN ba_summary TEXT"))
                        print("DEBUG: Added column ba_summary to interactions table")

            # Migrate test_queries table
            if inspector.has_table('test_queries'):
                existing_columns = [col['name']
                                    for col in inspector.get_columns('test_queries')]
                if 'llm_validation_result' not in existing_columns:
                    print(
                        "DEBUG: Adding llm_validation_result column to test_queries table")
                    with self.db_engine.begin() as connection:
                        connection.execute(
                            text("ALTER TABLE test_queries ADD COLUMN llm_validation_result TEXT"))
                        print(
                            "DEBUG: Added llm_validation_result column to test_queries table")

            # Migrate custom_tests table
            if inspector.has_table('custom_tests'):
                existing_columns = [col['name']
                                    for col in inspector.get_columns('custom_tests')]
                if 'llm_validation_result' not in existing_columns:
                    print(
                        "DEBUG: Adding llm_validation_result column to custom_tests table")
                    with self.db_engine.begin() as connection:
                        connection.execute(
                            text("ALTER TABLE custom_tests ADD COLUMN llm_validation_result TEXT"))
                        print(
                            "DEBUG: Added llm_validation_result column to custom_tests table")

                print("DEBUG: Schema migration completed successfully")
        except Exception as e:
            print(f"DEBUG: Schema migration error (non-critical): {e}")
            # Don't raise the exception as this is a migration issue and shouldn't break the app

    def create_chatbots_table(self):
        return Table(
            "chatbots", self.metadata,
            Column("chatbot_id", String(36), primary_key=True),
            Column("name", String(255), nullable=False),
            Column("db_type", String(50), nullable=True),
            Column("db_url", String(500), nullable=True),
            Column("schema_name", String(100), nullable=True),
            Column("selected_tables", Text, nullable=True),  # JSON array of selected table names
            Column("current_llm_name", String(100), default="COHERE"),
            Column("temperature", Float, default=0.7,
                   nullable=False),  # LLM temperature setting
            # Changed from String to DateTime for PostgreSQL
            Column("created_at", DateTime, server_default=func.now()),
            # <-- Added status column
            Column("status", String(50), nullable=True),
            Column("template_id", Integer, nullable=True),
            Column("efficiency", Float, nullable=True),
            # Knowledge base fields
            Column("industry", String(100), nullable=True),
            Column("vertical", String(100), nullable=True),
            Column("domain", String(100), nullable=True),
            Column("knowledge_base_file", String(500),
                   nullable=True),  # File path or content
            # BigQuery credentials
            Column("credentials_json", Text, nullable=True),
            # Enhanced semantic schema
            Column("semantic_schema_json", Text, nullable=True),
            # LLM key settings
            Column("llm_key_settings", Text, nullable=True)
        )

    def create_semantic_knowledge_cache_table(self):
        """
        Create the semantic_knowledge_cache table to store cached knowledge artifacts.
        Columns: id, chatbot_id, chatbot_name, knowledge_data
        """
        return Table(
            "semantic_knowledge_cache", self.metadata,
            Column("id", String(36), primary_key=True),
            Column("chatbot_id", String(36), nullable=False),
            Column("chatbot_name", String(255), nullable=True),
            Column("knowledge_data", Text, nullable=True)
        )

    def create_api_settings_table(self):
        """
        Create the api_settings table to store global API settings.
        Columns: setting_key (primary key), setting_value
        """
        return Table(
            "api_settings", self.metadata,
            Column("setting_key", String(100), primary_key=True),
            Column("setting_value", Text, nullable=True)
        )

    # ===== Semantic Knowledge Cache helpers =====
    def upsert_semantic_knowledge_cache(self, chatbot_id: str, chatbot_name: str, knowledge_data: dict) -> dict:
        """
        Insert or update the knowledge cache row for a chatbot.
        Uses chatbot_id as the logical key.
        """
        try:
            from uuid import uuid4
            payload = {
                "chatbot_id": chatbot_id,
                "chatbot_name": chatbot_name,
                "knowledge_data": json.dumps(knowledge_data) if not isinstance(knowledge_data, str) else knowledge_data,
            }
            with self.db_engine.begin() as connection:
                # Check existing by chatbot_id
                sel = self.semantic_knowledge_cache_table.select().where(
                    self.semantic_knowledge_cache_table.c.chatbot_id == chatbot_id
                )
                existing = connection.execute(sel).fetchone()
                if existing:
                    upd = (
                        self.semantic_knowledge_cache_table.update()
                        .where(self.semantic_knowledge_cache_table.c.chatbot_id == chatbot_id)
                        .values(**payload)
                    )
                    connection.execute(upd)
                    row = connection.execute(sel).fetchone()
                    return dict(row._mapping)
                else:
                    ins = self.semantic_knowledge_cache_table.insert().values(
                        id=str(uuid4()), **payload
                    )
                    connection.execute(ins)
                    row = connection.execute(sel).fetchone()
                    return dict(row._mapping) if row else payload
        except Exception as e:
            raise Exception(f"Error upserting semantic knowledge cache: {e}")

    def get_semantic_knowledge_cache(self, chatbot_id: str) -> dict | None:
        try:
            with self.db_engine.connect() as connection:
                sel = self.semantic_knowledge_cache_table.select().where(
                    self.semantic_knowledge_cache_table.c.chatbot_id == chatbot_id
                )
                row = connection.execute(sel).fetchone()
                if not row:
                    return None
                result = dict(row._mapping)
                try:
                    if isinstance(result.get("knowledge_data"), str):
                        result["knowledge_data"] = json.loads(result["knowledge_data"])
                except Exception:
                    pass
                return result
        except Exception as e:
            raise Exception(f"Error fetching semantic knowledge cache: {e}")

    def delete_semantic_knowledge_cache(self, chatbot_id: str) -> bool:
        try:
            with self.db_engine.begin() as connection:
                stmt = self.semantic_knowledge_cache_table.delete().where(
                    self.semantic_knowledge_cache_table.c.chatbot_id == chatbot_id
                )
                res = connection.execute(stmt)
                return res.rowcount > 0
        except Exception as e:
            raise Exception(f"Error deleting semantic knowledge cache: {e}")

    def create_chatbot(self, name, status=None, temperature=0.7):
        """
        Creates a new chatbot in the database.
        """
        try:
            chatbot_id = str(uuid4())
            now = datetime.utcnow()  # Use datetime object instead of string for PostgreSQL

            with self.db_engine.begin() as connection:
                values = {
                    'chatbot_id': chatbot_id,
                    'name': name,
                    'current_llm_name': "COHERE",
                    'temperature': temperature,
                    'created_at': now
                }
                if status is not None:
                    values['status'] = status
                query = insert(self.chatbots_table).values(**values)
                connection.execute(query)

            return {
                "chatbot_id": chatbot_id,
                "name": name,
                "current_llm_name": "COHERE",
                "temperature": temperature,
                "created_at": now.isoformat(),  # Convert to string for response
                "status": status
            }
        except Exception as e:
            raise Exception(f"Error creating chatbot: {e}")

    def get_chatbot(self, chatbot_id, default_template_name="Default Template"):
        """
        Fetches a chatbot by its ID, including the template name.
        If template_id is NULL, returns default_template_name.
        """
        try:
            proj = self.chatbots_table
            tmpl = self.templates_table

            # Use COALESCE: if tmpl.c.name is NULL (because template_id was NULL or no match), return default_template_name
            tmpl_name_expr = func.coalesce(tmpl.c.name, literal(
                default_template_name)).label("template_name")

            stmt = (
                select(
                    proj.c.chatbot_id,
                    proj.c.name.label("chatbot_name"),
                    proj.c.db_type,
                    proj.c.db_url,
                    proj.c.schema_name,
                    proj.c.selected_tables,  # Include selected_tables field
                    proj.c.current_llm_name,
                    proj.c.temperature,
                    proj.c.created_at,
                    proj.c.status,
                    proj.c.template_id,
                    proj.c.efficiency,  # Include efficiency field
                    proj.c.credentials_json,  # Include BigQuery credentials
                    tmpl_name_expr
                )
                .select_from(
                    proj.outerjoin(tmpl, proj.c.template_id == tmpl.c.id)
                )
                .where(proj.c.chatbot_id == chatbot_id)
            )

            with self.db_engine.connect() as connection:
                row = connection.execute(stmt).mappings().fetchone()

            return dict(row) if row else None

        except Exception as e:
            raise Exception(f"Error fetching chatbot with template: {e}")

    def get_all_chatbots(self):
        """
        Fetches all chatbots from the database.
        """
        try:
            with self.db_engine.connect() as connection:
                # Explicitly select columns to avoid issues with missing columns
                query = (
                    select(
                        self.chatbots_table.c.chatbot_id,
                        self.chatbots_table.c.name,
                        self.chatbots_table.c.db_type,
                        self.chatbots_table.c.db_url,
                        self.chatbots_table.c.schema_name,
                        self.chatbots_table.c.current_llm_name,
                        self.chatbots_table.c.temperature,
                        self.chatbots_table.c.created_at,
                        self.chatbots_table.c.status,
                        self.chatbots_table.c.template_id,
                        self.chatbots_table.c.efficiency,
                        self.chatbots_table.c.industry,
                        self.chatbots_table.c.vertical,
                        self.chatbots_table.c.domain,
                        self.chatbots_table.c.knowledge_base_file,
                        self.chatbots_table.c.credentials_json  # Include BigQuery credentials
                    )
                    .order_by(desc(self.chatbots_table.c.created_at))
                )
                result = connection.execute(query).fetchall()
                return [dict(row._mapping) for row in result]
        except Exception as e:
            raise Exception(f"Error fetching all chatbots: {e}")

    def update_chatbot(self, chatbot_id, db_type=None, db_url=None, schema_name=None, selected_tables=None, current_llm_name=None, status=None, template_id=None, efficiency=None, temperature=None, industry=None, vertical=None, domain=None, knowledge_base_file=None, credentials_json=None, llm_key_settings=None):
        """
        Updates a chatbot's database connection info, LLM settings, status, default template, efficiency, temperature, and knowledge base settings.
        """
        try:
            print(f"DEBUG: update_chatbot called for {chatbot_id} with db_type={db_type}, db_url={db_url}, schema_name={schema_name}, selected_tables={selected_tables}, status={status}, template_id={template_id}, efficiency={efficiency}, temperature={temperature}, industry={industry}, vertical={vertical}, domain={domain}")
            with self.db_engine.begin() as connection:
                update_values = {}
                if db_type is not None:
                    update_values["db_type"] = db_type
                if db_url is not None:
                    update_values["db_url"] = db_url
                if schema_name is not None:
                    update_values["schema_name"] = schema_name
                if selected_tables is not None:
                    update_values["selected_tables"] = selected_tables
                if current_llm_name is not None:
                    update_values["current_llm_name"] = current_llm_name
                if status is not None:
                    update_values["status"] = status
                if template_id is not None:
                    update_values["template_id"] = template_id
                if efficiency is not None:
                    update_values["efficiency"] = efficiency
                if temperature is not None:
                    update_values["temperature"] = temperature
                if industry is not None:
                    update_values["industry"] = industry
                if vertical is not None:
                    update_values["vertical"] = vertical
                if domain is not None:
                    update_values["domain"] = domain
                if knowledge_base_file is not None:
                    update_values["knowledge_base_file"] = knowledge_base_file
                if credentials_json is not None:
                    update_values["credentials_json"] = credentials_json
                # Support persisting per-chatbot LLM key settings JSON
                if llm_key_settings is not None:
                    update_values["llm_key_settings"] = llm_key_settings

                print(f"DEBUG: update_values to be set: {update_values}")
                if update_values:
                    query = (
                        self.chatbots_table.update()
                        .where(self.chatbots_table.c.chatbot_id == chatbot_id)
                        .values(**update_values)
                    )
                    result = connection.execute(query)
                    print(
                        f"DEBUG: update result rowcount: {getattr(result, 'rowcount', None)}")

                # Fetch and return the updated chatbot
                select_query = self.chatbots_table.select().where(
                    self.chatbots_table.c.chatbot_id == chatbot_id
                )
                result = connection.execute(select_query).fetchone()
                print(
                    f"DEBUG: updated chatbot row: {dict(result._mapping) if result else None}")
                return dict(result._mapping) if result else None
        except Exception as e:
            print(f"DEBUG: Exception in update_chatbot: {e}")
            raise Exception(f"Error updating chatbot: {e}")

    def delete_chatbot(self, chatbot_id):
        """
        Deletes a chatbot and all related data from the database.
        Cascade deletion order:
        1. interactions (via conversation_id from conversations)
        2. conversations (by chatbot_id)
        3. test_queries (by chatbot_id)
        4. custom_tests (by chatbot_id)
        5. chatbot_prompts (by chatbot_id)
        6. chatbots (finally delete the chatbot itself)
        """
        try:
            with self.db_engine.begin() as connection:
                # First get the chatbot to return it
                select_query = self.chatbots_table.select().where(
                    self.chatbots_table.c.chatbot_id == chatbot_id
                )
                chatbot = connection.execute(select_query).fetchone()

                if chatbot:
                    # 1. Delete interactions first (via conversation_id from conversations)
                    # Get all conversation IDs for this chatbot
                    conv_select = self.conversations_table.select().where(
                        self.conversations_table.c.chatbot_id == chatbot_id
                    )
                    conversations = connection.execute(conv_select).fetchall()

                    # Delete interactions for each conversation
                    for conv in conversations:
                        conv_id = conv.conversation_id
                        interactions_delete = self.interactions_table.delete().where(
                            self.interactions_table.c.conversation_id == conv_id
                        )
                        connection.execute(interactions_delete)

                    # 2. Delete conversations (by chatbot_id)
                    conversations_delete = self.conversations_table.delete().where(
                        self.conversations_table.c.chatbot_id == chatbot_id
                    )
                    connection.execute(conversations_delete)

                    # 3. Delete test_queries (by chatbot_id)
                    test_queries_delete = self.test_queries_table.delete().where(
                        self.test_queries_table.c.chatbot_id == chatbot_id
                    )
                    connection.execute(test_queries_delete)

                    # 4. Delete custom_tests (by chatbot_id)
                    custom_tests_delete = self.custom_tests_table.delete().where(
                        self.custom_tests_table.c.chatbot_id == chatbot_id
                    )
                    connection.execute(custom_tests_delete)

                    # 5. Delete chatbot_prompts (by chatbot_id)
                    chatbot_prompts_delete = self.chatbot_prompt_table.delete().where(
                        self.chatbot_prompt_table.c.chatbot_id == chatbot_id
                    )
                    connection.execute(chatbot_prompts_delete)

                    # 6. Delete semantic knowledge cache (by chatbot_id)
                    if hasattr(self, 'semantic_knowledge_cache_table'):
                        skc_delete = self.semantic_knowledge_cache_table.delete().where(
                            self.semantic_knowledge_cache_table.c.chatbot_id == chatbot_id
                        )
                        connection.execute(skc_delete)

                    # 7. Finally delete the chatbot itself
                    chatbot_delete = self.chatbots_table.delete().where(
                        self.chatbots_table.c.chatbot_id == chatbot_id
                    )
                    connection.execute(chatbot_delete)

                    return dict(chatbot._mapping)
                return None
        except Exception as e:
            raise Exception(f"Error deleting chatbot: {e}")

    def get_db_conn(self):
        # Return the database engine connection
        return self.db_engine

    def create_test_queries_table(self):
        return Table(
            "test_queries", self.metadata,
            # uuid for this specific LLM/temp run
            Column("query_id", String(36), primary_key=True),
            # uuid for the NL question (shared across LLM/temp runs)
            Column("question_id", String(36), nullable=False),
            # project/chatbot
            Column("chatbot_id", String(36), nullable=False),
            # LLM used for question generation
            Column("llm_using", String(100), nullable=False),
            # Temperature for question generation
            Column("temperature", Float, nullable=False, default=0.7),
            Column("original_sql", String(2000),
                   nullable=True),  # <-- Now nullable!
            Column("generated_question", String(1000), nullable=False),
            # Last regenerated SQL
            Column("generated_sql", String(2000), nullable=True),
            Column("score", Integer, nullable=True),
            # LLM used for regeneration
            Column("regen_llm_name", String(100), nullable=True),
            # Temperature for regeneration
            Column("regen_temperature", Float, nullable=True),
            # LLM-based validation result: "yes", "no", "ambiguity"
            Column("llm_validation_result", String(50), nullable=True),
            Column("created_at", DateTime, server_default=func.now())
        )

    def create_custom_tests_table(self):
        return Table(
            "custom_tests", self.metadata,
            Column("test_id", String(36), primary_key=True),               # uuid
            # project/chatbot
            Column("chatbot_id", String(36), nullable=False),
            # name of the test suite
            Column("test_name", String(255), nullable=False),
            # user's SQL query
            Column("original_sql", String(2000), nullable=False),
            # user's natural language question
            Column("natural_question", String(1000), nullable=False),
            # LLM generated SQL
            Column("generated_sql", String(2000), nullable=True),
            # 1 for correct, 0 for incorrect
            Column("score", Integer, nullable=True),
            # LLM that generated the SQL
            Column("llm_used", String(100), nullable=True),
            # temperature used
            Column("temperature", Float, nullable=True),
            # LLM-based validation result: "yes", "no", "ambiguity"
            Column("llm_validation_result", String(50), nullable=True),
            Column("created_at", DateTime, server_default=func.now()),
            Column("updated_at", DateTime,
                   server_default=func.now(), onupdate=func.now())
        )

    def create_conversations_table(self):
        return Table(
            "conversations", self.metadata,
            Column("conversation_id", String(36), primary_key=True),
            Column("chatbot_id", String(36), nullable=False),
            Column("conversation_name", String(255)),
            Column("conversation_type", String(50)),
            Column("template_id", Integer, nullable=True),
            # Changed from String to DateTime
            Column("start_time", DateTime, server_default=func.now()),
            # Changed from String to DateTime
            Column("end_time", DateTime, nullable=True),
            Column("status", String(50)),
            Column("owner", String(100))
        )

    def create_interactions_table(self):
        return Table(
            "interactions", self.metadata,
            Column("interaction_id", String(36), primary_key=True),
            Column("conversation_id", String(36), ForeignKey(
                "conversations.conversation_id")),
            Column("request", String(2000)),  # Increased size for PostgreSQL
            # Store the final result (answer) - using TEXT for unlimited size
            Column("final_result", Text),
            # Store the cleaned SQL query - increased size
            Column("cleaned_query", String(2000)),
            # Changed from String to DateTime
            Column("start_time", DateTime, server_default=func.now()),
            # Changed from String to DateTime
            Column("end_time", DateTime, nullable=True),
            Column("is_system_message", Boolean, nullable=False, server_default=text(
                'false')),  # Changed from '0' to 'false' for PostgreSQL
            # Store user rating: 1 for thumbs up, -1 for thumbs down, null for no rating
            Column("rating", Integer, nullable=True),
            # Cached BA insights summary text (nullable)
            Column("ba_summary", Text, nullable=True)
        )

    def create_interaction_results_table(self):
        """
        Stores result metadata per interaction. Actual rows are paged in a separate table.
        """
        return Table(
            "interaction_results", self.metadata,
            Column("interaction_id", String(36), primary_key=True),
            Column("total_rows", Integer, nullable=False),
            Column("total_columns", Integer, nullable=False),
            Column("columns_json", Text, nullable=False),  # JSON list of column names
            Column("page_size", Integer, nullable=False),
            Column("created_at", DateTime, server_default=func.now())
        )

    def create_interaction_result_pages_table(self):
        """
        Stores compressed JSON pages for a given interaction.
        """
        return Table(
            "interaction_result_pages", self.metadata,
            Column("interaction_id", String(36), ForeignKey("interaction_results.interaction_id"), primary_key=True),
            Column("page_index", Integer, primary_key=True),
            Column("row_start", Integer, nullable=False),
            Column("row_end", Integer, nullable=False),
            Column("rows_gzip_base64", Text, nullable=False),
            Column("created_at", DateTime, server_default=func.now())
        )

    def create_templates_table(self):
        return Table(
            "templates", self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(255), nullable=False),
            Column("description", String(500), nullable=True),
            Column("content", Text, nullable=False),
            Column("owner", String(100), nullable=False, default="admin"),
            Column("visibility", String(50),
                   nullable=False, default="private"),
            # Increase size for JSON data
            Column("shared_with", String(1000), nullable=True),
            Column("dataset_domain", String(200), nullable=True),
            Column("created_at", DateTime, server_default=func.now()),
            Column("updated_at", DateTime,
                   server_default=func.now(), onupdate=func.now())
        )

    def create_conversation(self, chatbot_id, conversation_name, status, owner, template_id=None, conversationType="DEFAULT"):
        """
        Inserts a new conversation into the database.
        """
        try:
            conversation_id = str(uuid4())
            now = datetime.utcnow()  # Use datetime object for PostgreSQL
            with self.db_engine.begin() as connection:
                query = insert(self.conversations_table).values(
                    conversation_id=conversation_id,
                    chatbot_id=chatbot_id,
                    conversation_name=conversation_name,
                    conversation_type=conversationType,
                    template_id=template_id,
                    start_time=now,
                    end_time=None,
                    status=status,
                    owner=owner
                )
                connection.execute(query)
            return {
                # Keep original key names for API compatibility
                "conversationId": conversation_id,
                "chatbot_id": chatbot_id,
                # Keep original key names for API compatibility
                "conversationName": conversation_name,
                # Keep original key names for API compatibility
                "conversationType": conversationType,
                "template_id": template_id,
                "startTime": now.isoformat(),  # Keep original key names for API compatibility
                "endTime": None,  # Keep original key names for API compatibility
                "status": status,
                "owner": owner
            }
        except Exception as e:
            raise Exception(f"Error creating conversation: {e}")

    def create_interaction(self, conversation_id: str, request_text: str, agent_response: dict = None, is_system_message: bool = False):
        """
        Creates a new interaction, correctly unpacking the agent_response dictionary
        and using datetime objects for timestamps.
        """
        try:
            interaction_id = str(uuid4())
            now = datetime.utcnow() # Use a datetime object

            interaction_data = {
                "interaction_id": interaction_id,
                "conversation_id": conversation_id,
                "request": request_text,
                "start_time": now, # Pass the datetime object
                "end_time": now,   # Pass the datetime object
                "is_system_message": is_system_message,
            }

            # Correctly unpack the agent_response dictionary
            if isinstance(agent_response, dict):
                # The final natural language answer
                final_result = agent_response.get("final_result")
                if final_result:
                    # If the result itself is a complex type, store as JSON string
                    if isinstance(final_result, (dict, list)):
                        interaction_data["final_result"] = json.dumps(final_result)
                    else:
                        interaction_data["final_result"] = str(final_result)
                
                cleaned_query = agent_response.get("cleaned_query")
                if cleaned_query:
                    interaction_data["cleaned_query"] = cleaned_query
            
            elif agent_response is not None:
                interaction_data["final_result"] = str(agent_response)

            with self.db_engine.begin() as connection:
                query = insert(self.interactions_table).values(interaction_data)
                connection.execute(query)
            
            return {
                "interactionId": interaction_data["interaction_id"],
                "conversationId": interaction_data["conversation_id"],
                "request": interaction_data["request"],
                "final_result": interaction_data.get("final_result"),
                "cleaned_query": interaction_data.get("cleaned_query"),
                "startTime": interaction_data["start_time"].isoformat(),
                "endTime": interaction_data["end_time"].isoformat(),
                "is_system_message": interaction_data["is_system_message"],
                "rating": interaction_data.get("rating")
            }
        except Exception as e:
            chatbot_db_logger.error(f"Error creating interaction for conv {conversation_id}: {e}", exc_info=True)
            raise Exception(f"Error creating interaction: {e}")

    def get_conversation(self, conversation_id):
        """
        Fetches a conversation by its ID, returning a camelCase dictionary.
        """
        try:
            with self.db_engine.connect() as connection:
                query = self.conversations_table.select().where(
                    self.conversations_table.c.conversation_id == conversation_id
                )
                result = connection.execute(query).fetchone()
                if result:
                    # Convert snake_case from DB to camelCase for the API/Service layer
                    row_dict = dict(result._mapping)
                    return {
                        "conversationId": row_dict.get("conversation_id"),
                        "chatbotId": row_dict.get("chatbot_id"), # <-- THIS WAS THE BUG. It said "chatbot_id"
                        "conversationName": row_dict.get("conversation_name"),
                        "conversationType": row_dict.get("conversation_type"),
                        "template_id": row_dict.get("template_id"),
                        "startTime": row_dict.get("start_time").isoformat() if row_dict.get("start_time") else None,
                        "endTime": row_dict.get("end_time").isoformat() if row_dict.get("end_time") else None,
                        "status": row_dict.get("status"),
                        "owner": row_dict.get("owner")
                    }
                return None
        except Exception as e:
            raise Exception(f"Error fetching conversation: {e}")
        
    def get_all_conversations(self, chatbot_id):
        """
        Fetches all conversations for a specific chatbot from the database.
        """
        try:
            with self.db_engine.connect() as connection:
                query = self.conversations_table.select().where(
                    self.conversations_table.c.chatbot_id == chatbot_id
                ).order_by(desc(self.conversations_table.c.start_time))
                result = connection.execute(query).fetchall()
                conversations = []
                for row in result:
                    # Convert snake_case to camelCase for API compatibility
                    row_dict = dict(row._mapping)
                    conversations.append({
                        "conversationId": row_dict.get("conversation_id"),
                        "chatbot_id": row_dict.get("chatbot_id"),
                        "conversationName": row_dict.get("conversation_name"),
                        "conversationType": row_dict.get("conversation_type"),
                        "template_id": row_dict.get("template_id"),
                        "startTime": row_dict.get("start_time").isoformat() if row_dict.get("start_time") else None,
                        "endTime": row_dict.get("end_time").isoformat() if row_dict.get("end_time") else None,
                        "status": row_dict.get("status"),
                        "owner": row_dict.get("owner")
                    })
                return conversations
        except Exception as e:
            raise Exception(f"Error fetching all conversations: {e}")

    def get_conversation_by_name(self, chatbot_id, conversation_name):
        """Fetches a conversation by name, returning a camelCase dictionary."""
        try:
            with self.db_engine.connect() as connection:
                stmt = self.conversations_table.select().where(
                    self.conversations_table.c.chatbot_id == chatbot_id,
                    self.conversations_table.c.conversation_name == conversation_name
                )
                result = connection.execute(stmt).fetchone()
                if result:
                    # Convert snake_case to camelCase for API compatibility
                    row_dict = dict(result._mapping)
                    return {
                        "conversationId": row_dict.get("conversation_id"),
                        "chatbotId": row_dict.get("chatbot_id"), # <-- THIS WAS THE BUG. It said "chatbot_id"
                        "conversationName": row_dict.get("conversation_name"),
                        "conversationType": row_dict.get("conversation_type"),
                        "template_id": row_dict.get("template_id"),
                        "startTime": row_dict.get("start_time").isoformat() if row_dict.get("start_time") else None,
                        "endTime": row_dict.get("end_time").isoformat() if row_dict.get("end_time") else None,
                        "status": row_dict.get("status"),
                        "owner": row_dict.get("owner")
                    }
                return None
        except Exception as e:
            raise Exception(f"Error fetching conversation by name: {e}")
        
    def get_all_interactions(self, conversation_id):
        """
        Fetches all interactions for a given conversation.
        """
        try:
            with self.db_engine.connect() as connection:
                query = self.interactions_table.select()
                result = connection.execute(query).fetchall()
                return [dict(row._mapping) for row in result]
        except Exception as e:
            raise Exception(f"Error fetching interactions: {e}")

    def delete_all_interactions(self, conv_id):
        with self.db_engine.begin() as connection:
            result = connection.execute(
                self.interactions_table.delete().where(
                    self.interactions_table.c.conversation_id == conv_id)
            )
            return result.rowcount

    def get_interaction_count(self, conversation_id):
        """
        Returns the total number of interactions for a conversation.
        """
        try:
            with self.db_engine.connect() as connection:
                result = connection.execute(
                    text(
                        "SELECT COUNT(*) AS cnt FROM interactions WHERE conversation_id = :conversation_id"),
                    {"conversation_id": conversation_id}
                ).scalar_one()
                return result
        except Exception as e:
            raise Exception(f"Error getting interaction count: {e}")

    def get_interactions_paginated(self, conversation_id, limit=5, offset=0):
        """
        Returns a batch of interactions plus pagination info for a conversation.
        Returns interactions in newest-first order (latest messages first).
        """
        with self.db_engine.begin() as connection:
            total = connection.execute(
                text(
                    "SELECT COUNT(*) AS cnt FROM interactions WHERE conversation_id = :conversation_id"),
                {"conversation_id": conversation_id}
            ).scalar_one()
            rows = connection.execute(
                text("""
                    SELECT *
                    FROM interactions
                    WHERE conversation_id = :conversation_id
                    ORDER BY start_time DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"conversation_id": conversation_id,
                    "limit": limit, "offset": offset}
            ).fetchall()

        interactions = []
        for row in rows:
            # Convert snake_case to camelCase for API compatibility
            row_dict = dict(row._mapping)
            interactions.append({
                "interactionId": row_dict.get("interaction_id"),
                "conversationId": row_dict.get("conversation_id"),
                "request": row_dict.get("request"),
                "final_result": row_dict.get("final_result"),
                "cleaned_query": row_dict.get("cleaned_query"),
                "startTime": row_dict.get("start_time").isoformat() if row_dict.get("start_time") else None,
                "endTime": row_dict.get("end_time").isoformat() if row_dict.get("end_time") else None,
                "is_system_message": row_dict.get("is_system_message"),
                "rating": row_dict.get("rating")
            })
        total_pages = math.ceil(total / limit) if limit else 1
        # Current page number (1-based)
        current_page = (offset // limit) + 1 if limit else 1
        last = current_page >= total_pages if total_pages > 0 else True

        return {
            "interactions": interactions,
            "total_count": total,
            "limit": limit,
            "last": last
        }

    def delete_conversation(self, conv_id):
        """
        Deletes a conversation and all its interactions from the database.
        Cascade deletion order:
        1. interactions (by conversation_id)
        2. conversations (by conversation_id)
        """
        try:
            with self.db_engine.begin() as connection:
                # 1. Delete all interactions for this conversation first
                interactions_delete = self.interactions_table.delete().where(
                    self.interactions_table.c.conversation_id == conv_id
                )
                connection.execute(interactions_delete)

                # 2. Then delete the conversation itself
                conversations_delete = self.conversations_table.delete().where(
                    self.conversations_table.c.conversation_id == conv_id
                )
                result = connection.execute(conversations_delete)
                return result.rowcount > 0
        except Exception as e:
            raise Exception(f"Error deleting conversation: {e}")
    # template functions

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        start_time = time.time()
        try:
            # Log first 100 chars of query
            chatbot_db_logger.info(f"Executing query: {query[:100]}...")

            with self.db_engine.connect() as connection:
                result = connection.execute(text(query), params or {})
                if fetch_one:
                    row = result.fetchone()
                    result_data = dict(row._mapping) if row else None
                    chatbot_db_logger.info("Query returned single row")
                    return result_data
                elif fetch_all:
                    rows = [dict(row._mapping) for row in result.fetchall()]
                    chatbot_db_logger.info(f"Query returned {len(rows)} rows")
                    return rows
                else:
                    return None
        except Exception as e:
            duration = time.time() - start_time
            chatbot_db_logger.error(
                f"Error executing query after {duration:.3f}s: {e}")
            raise
        finally:
            duration = time.time() - start_time
            if duration > 1.0:  # Log slow queries
                chatbot_db_logger.warning(
                    f"Slow query detected: {duration:.3f}s")

    def create_template(self, name, description, content, owner="admin", visibility="private", shared_with=None, dataset_domain=None):
        now = datetime.now()
        insert_query = """
            INSERT INTO templates (name, description, content, owner, visibility, shared_with, dataset_domain, created_at, updated_at)
            VALUES (:name, :description, :content, :owner, :visibility, :shared_with, :dataset_domain, :created_at, :updated_at)
            RETURNING id
        """
        select_query = "SELECT * FROM templates WHERE id = :id"
        with self.db_engine.begin() as connection:
            result = connection.execute(
                text(insert_query),
                {
                    "name": name,
                    "description": description,
                    "content": content,
                    "owner": owner,
                    "visibility": visibility,
                    "shared_with": json.dumps(shared_with) if shared_with else None,
                    "dataset_domain": dataset_domain,
                    "created_at": now,
                    "updated_at": now
                }
            )
            # For PostgreSQL, use RETURNING to get the last inserted ID
            last_id = result.fetchone()[0] if result.rowcount > 0 else None
            if last_id:
                row = connection.execute(text(select_query), {
                                         "id": last_id}).fetchone()
                if row:
                    template_dict = dict(row._mapping)
                    # Parse shared_with back to list if it exists
                    if template_dict.get('shared_with'):
                        template_dict['shared_with'] = json.loads(
                            template_dict['shared_with'])
                    return template_dict
            return None

    def get_all_templates(self, owner=None, visibility=None, chatbot_id=None):
        """
        Get all templates with optional filtering.

        Args:
            owner: Filter by template owner
            visibility: Filter by visibility (public, private, shared)
            chatbot_id: When provided, include templates that are shared with this chatbot
        """
        conditions = []
        params = {}

        if owner:
            conditions.append("owner = :owner")
            params["owner"] = owner

        if visibility:
            conditions.append("visibility = :visibility")
            params["visibility"] = visibility

        # Build base query
        base_query = "SELECT * FROM templates"
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        # If chatbot_id is provided, also include shared templates
        if chatbot_id:
            if conditions:
                base_query += " OR (visibility = 'shared' AND shared_with LIKE :chatbot_pattern)"
            else:
                base_query += " WHERE visibility = 'shared' AND shared_with LIKE :chatbot_pattern"
            params["chatbot_pattern"] = f'%"{chatbot_id}"%'

        base_query += " ORDER BY created_at DESC;"

        templates = self.execute_query(
            base_query, params, fetch_all=True) or []

        # Parse shared_with JSON field for each template
        for template in templates:
            if template.get('shared_with'):
                try:
                    template['shared_with'] = json.loads(
                        template['shared_with'])
                except (json.JSONDecodeError, TypeError):
                    template['shared_with'] = []
            else:
                template['shared_with'] = []
            # Ensure dataset_domain is present
            if 'dataset_domain' not in template:
                template['dataset_domain'] = None

        return templates

    def get_template_by_id(self, template_id):
        query = "SELECT * FROM templates WHERE id = :id;"
        template = self.execute_query(
            query, {"id": template_id}, fetch_one=True)
        if template:
            if template.get('shared_with'):
                try:
                    template['shared_with'] = json.loads(
                        template['shared_with'])
                except (json.JSONDecodeError, TypeError):
                    template['shared_with'] = []
            else:
                template['shared_with'] = []
            if 'dataset_domain' not in template:
                template['dataset_domain'] = None
        return template

    def update_template(self, template_id, name=None, description=None, content=None, owner=None, visibility=None, shared_with=None, dataset_domain=None):
        fields = []
        params = {"id": template_id, "updated_at": datetime.utcnow()}

        if name is not None:
            fields.append("name = :name")
            params["name"] = name
        if description is not None:
            fields.append("description = :description")
            params["description"] = description
        if content is not None:
            fields.append("content = :content")
            params["content"] = content
        if owner is not None:
            fields.append("owner = :owner")
            params["owner"] = owner
        if visibility is not None:
            fields.append("visibility = :visibility")
            params["visibility"] = visibility
        if shared_with is not None:
            fields.append("shared_with = :shared_with")
            params["shared_with"] = json.dumps(
                shared_with) if shared_with else None
        if dataset_domain is not None:
            fields.append("dataset_domain = :dataset_domain")
            params["dataset_domain"] = dataset_domain

        if not fields:
            raise ValueError("No fields provided for update")

        query = f"""
        UPDATE templates SET {', '.join(fields)}, updated_at = :updated_at
        WHERE id = :id;
        """
        with self.db_engine.begin() as connection:
            connection.execute(text(query), params)
            # Fetch the updated row
            select_query = "SELECT * FROM templates WHERE id = :id"
            row = connection.execute(text(select_query), {
                                     "id": template_id}).fetchone()
            if row:
                template_dict = dict(row._mapping)
                # Parse shared_with back to list if it exists
                if template_dict.get('shared_with'):
                    try:
                        template_dict['shared_with'] = json.loads(
                            template_dict['shared_with'])
                    except (json.JSONDecodeError, TypeError):
                        template_dict['shared_with'] = []
                else:
                    template_dict['shared_with'] = []
                if 'dataset_domain' not in template_dict:
                    template_dict['dataset_domain'] = None
                return template_dict
            return None

    def delete_template(self, template_id):
        """Deletes a template by ID."""
        try:
            with self.db_engine.begin() as connection:
                query = self.templates_table.delete().where(
                    self.templates_table.c.id == template_id)
                connection.execute(query)
        except Exception as e:
            raise Exception(f"Error deleting template: {e}")

    def get_interaction_cleaned_query(self, conversation_id, interaction_id):
        """
        Gets the cleaned query for a specific interaction in a conversation.

        Args:
            conversation_id (str): The ID of the conversation
            interaction_id (str): The ID of the interaction

        Returns:
            dict: Dictionary containing interaction_id, conversation_id, and cleaned_query
            None: If interaction not found or no cleaned query exists
        """
        try:
            # First verify the conversation exists
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                return None

            # Get the specific interaction
            query = text("""
                SELECT interaction_id, conversation_id, cleaned_query 
                FROM interactions 
                WHERE conversation_id = :conv_id 
                AND interaction_id = :int_id
            """)

            with self.db_engine.connect() as conn:
                result = conn.execute(
                    query, {"conv_id": conversation_id, "int_id": interaction_id}).fetchone()

            if not result:
                return None

            # Convert row to dict
            interaction = dict(result._mapping)

            # Return None if no cleaned query exists
            if not interaction.get("cleaned_query"):
                return None

            return {
                "interaction_id": interaction["interaction_id"],
                "conversation_id": interaction["conversation_id"],
                "cleaned_query": interaction["cleaned_query"]
            }

        except Exception as e:
            raise Exception(f"Error getting interaction cleaned query: {e}")

    def get_conversations_by_template_id(self, template_id):
        with self.db_engine.connect() as connection:
            result = connection.execute(
                self.conversations_table.select().where(
                    self.conversations_table.c.template_id == template_id)
            ).fetchall()
            return [dict(row._mapping) for row in result]

    def get_benchmark_details(self, chatbot_id):
        with self.db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT original_sql, generated_question, generated_sql, score
                    FROM test_queries
                    WHERE chatbot_id = :cid
                    ORDER BY query_id
                """),
                {"cid": chatbot_id}
            )
            return result.fetchall()

    def get_performance_metrics(self, chatbot_id, llm_name=None, temperature=None):
        """
        Gets performance metrics for a chatbot including efficiency and test query count.
        Filters by LLM and temperature if provided.
        Only considers rows where generated_sql IS NOT NULL AND generated_sql != ''.
        """
        try:
            with self.db_engine.connect() as conn:
                # First get the chatbot to check its current settings
                chatbot = self.get_chatbot(chatbot_id)
                if not chatbot:
                    return None
                # Use current chatbot settings if not provided
                current_llm = llm_name or chatbot.get('current_llm_name')
                current_temp = temperature if temperature is not None else chatbot.get(
                    'temperature', 0.7)
                # Get test query metrics (only where generated_sql is present)
                test_query_result = conn.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_queries,
                            SUM(CASE WHEN score = 1 THEN 1 ELSE 0 END) as correct_queries,
                            CASE 
                                WHEN COUNT(*) > 0 THEN 
                                    CAST(SUM(CASE WHEN score = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) 
                                ELSE 0 
                            END as efficiency
                        FROM test_queries
                        WHERE chatbot_id = :cid AND llm_using = :llm AND temperature = :temp
                          AND generated_sql IS NOT NULL AND generated_sql != ''
                    """),
                    {"cid": chatbot_id, "llm": current_llm, "temp": current_temp}
                ).fetchone()
                if test_query_result:
                    metrics = dict(test_query_result._mapping)
                    # Update chatbot efficiency in the main table if we have a valid efficiency
                    if metrics['efficiency'] > 0:
                        self.update_chatbot(
                            chatbot_id, efficiency=metrics['efficiency'])
                    return {
                        'total_queries': metrics['total_queries'],
                        'correct_queries': metrics['correct_queries'],
                        'efficiency': metrics['efficiency'],
                        'llm_name': current_llm,
                        'temperature': current_temp
                    }
                return {
                    'total_queries': 0,
                    'correct_queries': 0,
                    'efficiency': chatbot.get('efficiency', 0) or 0,
                    'llm_name': current_llm,
                    'temperature': current_temp
                }
        except Exception as e:
            raise Exception(f"Error getting performance metrics: {e}")

    def update_interaction_rating(self, conversation_id, interaction_id, rating):
        """
        Updates the rating for a specific interaction.

        Args:
            conversation_id (str): The ID of the conversation
            interaction_id (str): The ID of the interaction
            rating (int): The rating value (1 for thumbs up, -1 for thumbs down)

        Returns:
            bool: True if rating was updated successfully, False otherwise
        """
        try:
            with self.db_engine.begin() as connection:
                result = connection.execute(
                    self.interactions_table.update()
                    .where(self.interactions_table.c.conversation_id == conversation_id)
                    .where(self.interactions_table.c.interaction_id == interaction_id)
                    .values(rating=rating)
                )
                return result.rowcount > 0
        except Exception as e:
            raise Exception(f"Error updating interaction rating: {e}")

    def get_or_generate_ba_summary(self, interaction_id, generator_fn):
        """
        Returns cached BA summary if present; otherwise generates via generator_fn,
        stores it, and returns the value.

        Args:
            interaction_id (str): ID of the interaction
            generator_fn (Callable[[], str]): Function that returns the BA summary text
        """
        try:
            with self.db_engine.begin() as connection:
                row = connection.execute(
                    self.interactions_table.select()
                    .with_only_columns(self.interactions_table.c.ba_summary)
                    .where(self.interactions_table.c.interaction_id == interaction_id)
                ).fetchone()

                cached = row[0] if row else None
                if cached:
                    return cached

                summary = generator_fn()
                connection.execute(
                    self.interactions_table.update()
                    .where(self.interactions_table.c.interaction_id == interaction_id)
                    .values(ba_summary=summary)
                )
                return summary
        except Exception as e:
            raise Exception(f"Error getting/generating BA summary: {e}")

    def update_ba_summary(self, interaction_id: str, summary: str):
        """Force-update BA summary for an interaction."""
        try:
            with self.db_engine.begin() as connection:
                result = connection.execute(
                    self.interactions_table.update()
                    .where(self.interactions_table.c.interaction_id == interaction_id)
                    .values(ba_summary=summary)
                )
                return result.rowcount > 0
        except Exception as e:
            raise Exception(f"Error updating BA summary: {e}")

    def get_interaction_rating(self, conversation_id, interaction_id):
        """
        Gets the rating for a specific interaction.

        Args:
            conversation_id (str): The ID of the conversation
            interaction_id (str): The ID of the interaction

        Returns:
            int or None: The rating value (1 for thumbs up, -1 for thumbs down, None for no rating)
        """
        try:
            with self.db_engine.connect() as connection:
                result = connection.execute(
                    self.interactions_table.select()
                    .where(self.interactions_table.c.conversation_id == conversation_id)
                    .where(self.interactions_table.c.interaction_id == interaction_id)
                ).fetchone()

                if result:
                    return dict(result._mapping).get("rating")
                return None
        except Exception as e:
            raise Exception(f"Error getting interaction rating: {e}")

    def create_chatbot_prompt_table(self):
        return Table(
            "chatbot_prompts", self.metadata,
            Column("chatbot_id", String(36), primary_key=True),
            Column("prompt", Text, nullable=False),
            Column("created_at", DateTime, server_default=func.now()),
            Column("updated_at", DateTime,
                   server_default=func.now(), onupdate=func.now())
        )

    def create_chatbot_prompt(self, chatbot_id, prompt):
        """
        Creates or updates a chatbot prompt in the database.
        """
        try:
            with self.db_engine.begin() as connection:
                # Check if prompt already exists for this chatbot
                select_query = self.chatbot_prompt_table.select().where(
                    self.chatbot_prompt_table.c.chatbot_id == chatbot_id
                )
                existing_prompt = connection.execute(select_query).fetchone()

                if existing_prompt:
                    # Update existing prompt
                    update_query = (
                        self.chatbot_prompt_table.update()
                        .where(self.chatbot_prompt_table.c.chatbot_id == chatbot_id)
                        .values(prompt=prompt, updated_at=func.now())
                    )
                    connection.execute(update_query)

                    # Get the updated prompt
                    result = connection.execute(select_query).fetchone()
                    return dict(result._mapping)
                else:
                    # Create new prompt
                    insert_query = self.chatbot_prompt_table.insert().values(
                        chatbot_id=chatbot_id,
                        prompt=prompt
                    )
                    connection.execute(insert_query)

                    # Get the newly created prompt
                    result = connection.execute(select_query).fetchone()
                    return dict(result._mapping)

        except Exception as e:
            raise Exception(f"Error creating/updating chatbot prompt: {e}")

    def get_chatbot_prompt(self, chatbot_id):
        """
        Retrieves the prompt for a specific chatbot.
        """
        try:
            with self.db_engine.connect() as connection:
                select_query = self.chatbot_prompt_table.select().where(
                    self.chatbot_prompt_table.c.chatbot_id == chatbot_id
                )
                result = connection.execute(select_query).fetchone()
                return dict(result._mapping) if result else None
        except Exception as e:
            raise Exception(f"Error retrieving chatbot prompt: {e}")

    def delete_chatbot_prompt(self, chatbot_id):
        """
        Deletes a chatbot's prompt from the database.
        """
        try:
            with self.db_engine.begin() as connection:
                query = self.chatbot_prompt_table.delete().where(
                    self.chatbot_prompt_table.c.chatbot_id == chatbot_id
                )
                connection.execute(query)
            return True
        except Exception as e:
            raise Exception(f"Error deleting chatbot prompt: {e}")

    # ========== CUSTOM TESTS MANAGEMENT ==========

    def create_custom_test(self, chatbot_id, test_name, original_sql, natural_question):
        """
        Creates a new custom test in the database.
        """
        try:
            test_id = str(uuid4())
            with self.db_engine.begin() as connection:
                query = insert(self.custom_tests_table).values(
                    test_id=test_id,
                    chatbot_id=chatbot_id,
                    test_name=test_name,
                    original_sql=original_sql,
                    natural_question=natural_question
                )
                connection.execute(query)
            return {
                "test_id": test_id,
                "chatbot_id": chatbot_id,
                "test_name": test_name,
                "original_sql": original_sql,
                "natural_question": natural_question
            }
        except Exception as e:
            raise Exception(f"Error creating custom test: {e}")

    def get_custom_tests(self, chatbot_id, test_name=None):
        """
        Fetches custom tests for a chatbot, optionally filtered by test name.
        """
        try:
            with self.db_engine.connect() as connection:
                query = self.custom_tests_table.select().where(
                    self.custom_tests_table.c.chatbot_id == chatbot_id
                )
                if test_name:
                    query = query.where(
                        self.custom_tests_table.c.test_name == test_name)
                query = query.order_by(
                    desc(self.custom_tests_table.c.created_at))
                result = connection.execute(query).fetchall()
                return [dict(row._mapping) for row in result]
        except Exception as e:
            raise Exception(f"Error fetching custom tests: {e}")

    def get_custom_test_suites(self, chatbot_id):
        """
        Gets all unique test suite names for a chatbot.
        """
        try:
            with self.db_engine.connect() as connection:
                query = select(self.custom_tests_table.c.test_name).where(
                    self.custom_tests_table.c.chatbot_id == chatbot_id
                ).distinct()
                result = connection.execute(query).fetchall()
                return [row[0] for row in result]
        except Exception as e:
            raise Exception(f"Error fetching custom test suites: {e}")

    def update_custom_test_result(self, test_id, generated_sql, score, llm_used, temperature, llm_validation_result=None):
        """
        Updates a custom test with the LLM-generated SQL and validation result.
        """
        try:
            with self.db_engine.begin() as connection:
                values = {
                    "generated_sql": generated_sql,
                    "score": score,
                    "llm_used": llm_used,
                    "temperature": temperature
                }
                if llm_validation_result is not None:
                    values["llm_validation_result"] = llm_validation_result

                query = (
                    self.custom_tests_table.update()
                    .where(self.custom_tests_table.c.test_id == test_id)
                    .values(**values)
                )
                connection.execute(query)
            return True
        except Exception as e:
            raise Exception(f"Error updating custom test result: {e}")

    def delete_custom_test(self, test_id):
        """
        Deletes a custom test from the database.
        """
        try:
            with self.db_engine.begin() as connection:
                query = self.custom_tests_table.delete().where(
                    self.custom_tests_table.c.test_id == test_id
                )
                connection.execute(query)
            return True
        except Exception as e:
            raise Exception(f"Error deleting custom test: {e}")

    def get_custom_test_metrics(self, chatbot_id, test_name=None, llm_used=None):
        """
        Gets performance metrics for custom tests.
        """
        try:
            with self.db_engine.connect() as conn:
                # Build the SQL query dynamically
                sql_query = """
                    SELECT 
                        COUNT(*) as total_tests,
                        SUM(CASE WHEN score = 1 THEN 1 ELSE 0 END) as correct_tests,
                        CASE 
                            WHEN COUNT(*) > 0 THEN 
                                CAST(SUM(CASE WHEN score = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) 
                            ELSE 0 
                        END as efficiency
                    FROM custom_tests
                    WHERE chatbot_id = :cid
                """

                params = {"cid": chatbot_id}

                if test_name:
                    sql_query += " AND test_name = :test_name"
                    params["test_name"] = test_name

                if llm_used:
                    sql_query += " AND llm_used = :llm_used"
                    params["llm_used"] = llm_used

                result = conn.execute(text(sql_query), params).fetchone()

                return {
                    "total_tests": result.total_tests,
                    "correct_tests": result.correct_tests,
                    "efficiency": result.efficiency
                }
        except Exception as e:
            raise Exception(f"Error getting custom test metrics: {e}")

    # Removed legacy extract_sample_data() – sample rows are now added
    # dynamically in QueryGeneratorAgent for intent-selected tables only.

    def extract_schema_info(self, app_db_util):
        """
        Extracts database schema information from the application database.
        Returns a formatted string with schema details for each table.
        """
        try:
            schema_text = "\n\n--- DATABASE SCHEMA ---\n"

            # Get all table names from the application database
            inspector = inspect(app_db_util.db_engine)
            table_names = inspector.get_table_names()

            if not table_names:
                return schema_text + "No tables found in the database.\n"

            for table_name in table_names:
                try:
                    # Get table schema information
                    columns = inspector.get_columns(table_name)

                    schema_text += f"\n{table_name.upper()} TABLE:\n"
                    for column in columns:
                        col_name = column['name']
                        col_type = str(column['type'])
                        nullable = "NULL" if column.get(
                            'nullable', True) else "NOT NULL"
                        default = column.get('default', '')
                        primary_key = "PRIMARY KEY" if column.get(
                            'primary_key', False) else ""

                        schema_text += f"  - {col_name}: {col_type} {nullable}"
                        if default:
                            schema_text += f" DEFAULT {default}"
                        if primary_key:
                            schema_text += f" {primary_key}"
                        schema_text += "\n"

                    # Get foreign key information
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    if foreign_keys:
                        schema_text += f"  Foreign Keys:\n"
                        for fk in foreign_keys:
                            schema_text += f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}\n"

                    schema_text += "\n"

                except Exception as table_error:
                    schema_text += f"\n{table_name.upper()}: Error extracting schema - {str(table_error)}\n\n"
                    continue

            return schema_text

        except Exception as e:
            return f"\n\n--- DATABASE SCHEMA ---\nError extracting schema: {str(e)}\n"

    def generate_enhanced_prompt(self, chatbot_id, app_db_util, include_sample_data=False, preview_content=None):
        """
        Generates the final prompt for the LLM by combining:
        1. Template content from templates table
        2. Database schema information (if sample data not included)
        3. Sample data from all tables (if selected)


        Args:
            chatbot_id: The chatbot ID
            app_db_util: Database utility for the user's database
            include_sample_data: If True, include sample data instead of schema
            preview_content: Optional preview content (deprecated)
        """
        try:
            enhanced_prompt = ""

            # 1. Get template content from templates table
            template_content = self.get_template_content_for_chatbot(
                chatbot_id)
            if template_content:
                enhanced_prompt += template_content
                enhanced_prompt += "\n\n"

            # Note: Legacy inclusion of global sample data/schema is removed.
            # Prompt construction now happens within QueryGeneratorAgent with
            # intent-scoped samples.

            return enhanced_prompt
        except Exception as e:
            return f"Error generating enhanced prompt: {str(e)}"

    def get_template_content_for_chatbot(self, chatbot_id):
        """
        Gets the template content for a chatbot from the templates table.
        """
        try:
            # First get the chatbot to find its template_id
            chatbot = self.get_chatbot(chatbot_id)
            if not chatbot:
                return None

            template_id = chatbot.get("template_id")
            if not template_id:
                return None

            # Get the template content from templates table
            template = self.get_template_by_id(template_id)
            if not template:
                return None

            return template.get("content")

        except Exception as e:
            print(
                f"Error getting template content for chatbot {chatbot_id}: {e}")
            return None

    def store_semantic_schema(self, chatbot_id: str, semantic_schema_json: str) -> bool:
        """
        Store the semantic schema JSON for a chatbot.

        Args:
            chatbot_id: The chatbot ID
            semantic_schema_json: JSON string of the semantic schema

        Returns:
            True if successful, False otherwise
        """
        try:
            # 🔍 LOGGING: Track schema updates in database
            print(f"\n{'='*80}")
            print(f"💾 DATABASE: Storing semantic schema")
            print(f"{'='*80}")
            print(f"🤖 Chatbot ID: {chatbot_id}")
            print(f"📊 Schema JSON Length: {len(semantic_schema_json)} characters")
            
            # Parse and log key schema information
            try:
                schema_data = json.loads(semantic_schema_json)
                print(f"📋 Tables: {len(schema_data.get('tables', {}))}")
                print(f"📈 Metrics: {len(schema_data.get('metrics', []))}")
                
                # Log business metrics being stored
                for metric in schema_data.get('metrics', []):
                    print(f"  📊 {metric.get('name', 'Unknown')}: {metric.get('expression', 'No expression')}")
                
                # Log tables with business context
                for table_name, table_data in schema_data.get('tables', {}).items():
                    if table_data.get('business_context'):
                        print(f"  📋 {table_name}: {table_data.get('business_context')}")
                
                # Log columns with business context
                for table_name, table_data in schema_data.get('tables', {}).items():
                    for col_name, col_data in table_data.get('columns', {}).items():
                        if col_data.get('business_context'):
                            print(f"  📝 {table_name}.{col_name}: {col_data.get('business_context')}")
                            
            except json.JSONDecodeError as e:
                print(f"⚠️  Warning: Could not parse schema JSON for logging: {e}")
            
            print(f"{'='*80}\n")
            
            with self.db_engine.begin() as connection:
                query = (
                    self.chatbots_table.update()
                    .where(self.chatbots_table.c.chatbot_id == chatbot_id)
                    .values(semantic_schema_json=semantic_schema_json)
                )
                result = connection.execute(query)
                print(f"✅ Schema successfully stored in database (rows affected: {result.rowcount})")
                return result.rowcount > 0
        except Exception as e:
            print(f"❌ Error storing semantic schema for chatbot {chatbot_id}: {e}")
            return False

    def get_semantic_schema(self, chatbot_id: str) -> str:
        """
        Retrieve the semantic schema JSON for a chatbot.

        Args:
            chatbot_id: The chatbot ID

        Returns:
            JSON string of the semantic schema or None if not found
        """
        try:
            with self.db_engine.connect() as connection:
                query = (
                    select(self.chatbots_table.c.semantic_schema_json)
                    .where(self.chatbots_table.c.chatbot_id == chatbot_id)
                )
                result = connection.execute(query).fetchone()
                return result.semantic_schema_json if result else None
        except Exception as e:
            print(
                f"Error retrieving semantic schema for chatbot {chatbot_id}: {e}")
            return None

    def generate_enhanced_prompt_with_semantic_schema(self, chatbot_id, include_sample_data=False):
        """
        Generate enhanced prompt using semantic schema instead of raw schema.

        Args:
            chatbot_id: The chatbot ID
            include_sample_data: If True, include sample data instead of semantic schema

        Returns:
            Enhanced prompt string
        """
        try:
            enhanced_prompt = ""

            # 1. Get template content from templates table
            template_content = self.get_template_content_for_chatbot(
                chatbot_id)
            if template_content:
                enhanced_prompt += template_content
                enhanced_prompt += "\n\n"

            # 2. Add either semantic schema OR sample data based on user preference
            if include_sample_data:
                # User selected sample data - include sample data, skip schema
                # Note: This would require app_db_util which we don't have here
                enhanced_prompt += "\n\n--- SAMPLE DATA MODE ---\nNote: Sample data mode requires database connection.\n"
            else:
                # User didn't select sample data - include semantic schema
                semantic_schema_json = self.get_semantic_schema(chatbot_id)
                if semantic_schema_json:
                    enhanced_prompt += f"--- ENHANCED DATABASE SCHEMA ---\n{semantic_schema_json}\n"
                else:
                    enhanced_prompt += "\n--- DATABASE SCHEMA ---\nNo enhanced schema available.\n"

            return enhanced_prompt
        except Exception as e:
            return f"Error generating enhanced prompt with semantic schema: {str(e)}"
