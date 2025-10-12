import os
import glob
import time
import json
import logging
from typing import Optional
from sqlalchemy import create_engine, MetaData, text, inspect

from config import create_database_engine, get_app_db_pool_config

# Configure logging for this utility
app_db_logger = logging.getLogger('app_database')


def cleanup_old_credential_files(max_age_hours: int = 24):
    """
    Cleans up old BigQuery credential files from the temp directory.
    """
    try:
        # Define temp directory relative to this file's location
        temp_dir = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), '..', 'temp_creds')
        if not os.path.exists(temp_dir):
            return

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        cred_files = glob.glob(os.path.join(temp_dir, 'bigquery_creds_*.json'))

        for cred_file in cred_files:
            try:
                if (current_time - os.path.getmtime(cred_file)) > max_age_seconds:
                    os.remove(cred_file)
                    logging.info(
                        f"Cleaned up old credential file: {cred_file}")
            except Exception as e:
                logging.warning(
                    f"Error cleaning up credential file {cred_file}: {e}")
    except Exception as e:
        logging.error(f"Error in cleanup_old_credential_files: {e}")


class AppDbUtil:
    def __init__(self, db_url: str, credentials_json: Optional[str] = None):
        app_db_logger.info(f"Initializing AppDbUtil with db_url: {db_url}")
        if not db_url:
            raise ValueError("db_url must be provided")

        self.credentials_json = credentials_json
        self.temp_creds_file = None

        # Handle BigQuery credentials if provided
        if credentials_json and 'bigquery://' in db_url:
            try:
                # Create temporary credentials file with better naming and persistence
                creds_data = json.loads(credentials_json)

                # Create a more persistent temp file name based on content hash
                import hashlib
                creds_hash = hashlib.md5(credentials_json.encode()).hexdigest()
                temp_filename = f"bigquery_creds_{creds_hash}.json"

                # Use a dedicated temp directory for BigQuery credentials
                temp_dir = os.path.join(
                    os.path.dirname(__file__), 'temp_creds')
                os.makedirs(temp_dir, exist_ok=True)

                self.temp_creds_file = os.path.join(temp_dir, temp_filename)

                # Only create file if it doesn't exist or if content is different
                if not os.path.exists(self.temp_creds_file):
                    with open(self.temp_creds_file, 'w') as f:
                        json.dump(creds_data, f)
                    app_db_logger.info(
                        f"Created BigQuery credentials file: {self.temp_creds_file}")
                else:
                    app_db_logger.info(
                        f"Using existing BigQuery credentials file: {self.temp_creds_file}")

                # Set environment variable for BigQuery authentication
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.temp_creds_file
                app_db_logger.info(
                    f"BigQuery credentials set from file: {self.temp_creds_file}")
            except Exception as e:
                app_db_logger.error(f"Error setting BigQuery credentials: {e}")
                raise ValueError(f"Invalid BigQuery credentials: {str(e)}")

        # Use the new database configuration with proper connection pooling
        pool_config = get_app_db_pool_config()
        self.db_engine = create_database_engine(db_url, pool_config)
        self.metadata = MetaData()

        # Log connection pool status after initialization
        if hasattr(self.db_engine, 'pool'):
            app_db_logger.info(
                f"Database engine initialized with pool size: {self.db_engine.pool.size()}")

        self.initialize_tables()

    def __del__(self):
        """Cleanup temporary credentials file and database engine."""
        # Clean up database engine
        if hasattr(self, 'db_engine') and self.db_engine:
            try:
                self.db_engine.dispose()
            except Exception:
                pass

    def cleanup_credentials(self):
        """Manually cleanup credentials file when done."""
        if self.temp_creds_file and os.path.exists(self.temp_creds_file):
            try:
                logging.debug(
                    f"Keeping credentials file for reuse: {self.temp_creds_file}")
            except Exception as e:
                logging.debug(f"Error handling credentials file: {e}")

    def initialize_tables(self):
        """
        Creates all defined tables in the database if they don't exist.
        """
        try:
            # Create all tables in the database
            self.metadata.create_all(self.db_engine)
            logging.debug("Tables initialized successfully")
            return True
        except Exception as e:
            logging.info("DEBUG: Tables initialized successfully")
            raise Exception(f"Failed to initialize tables: {e}")

    # Removed legacy extract_sample_data() method – sample rows are now added
    # dynamically in QueryGeneratorAgent only for intent-selected tables.

    def execute_query(self, query, params=None, fetch_all=False):
        """
        Execute a SQL query and return results.
        """
        start_time = time.time()
        try:
            # Log first 100 chars of query
            app_db_logger.info(f"Executing query: {query[:100]}...")

            with self.db_engine.connect() as connection:
                if params:
                    result = connection.execute(text(query), params)
                else:
                    result = connection.execute(text(query))

                if fetch_all:
                    rows = [dict(row._mapping) for row in result.fetchall()]
                    app_db_logger.info(f"Query returned {len(rows)} rows")
                    return rows
                else:
                    row = result.fetchone()
                    app_db_logger.info("Query returned single row")
                    return row
        except Exception as e:
            duration = time.time() - start_time
            app_db_logger.error(
                f"Error executing query after {duration:.3f}s: {e}")
            raise e
        finally:
            duration = time.time() - start_time
            if duration > 1.0:  # Log slow queries
                app_db_logger.warning(f"Slow query detected: {duration:.3f}s")

    def get_table_info(self, table_name):
        """
        Get information about a specific table.
        """
        try:
            inspector = inspect(self.db_engine)
            columns = inspector.get_columns(table_name)
            return {
                'table_name': table_name,
                'columns': [col['name'] for col in columns]
            }
        except Exception as e:
            logging.info(f"Error getting table info for {table_name}: {e}")
            return None

    def get_db_conn(self):
        """
        Get a database connection from the engine.
        """
        return self.db_engine.connect()

    def get_credentials_file_path(self):
        """Get the path to the credentials file if it exists."""
        return self.temp_creds_file if self.temp_creds_file and os.path.exists(self.temp_creds_file) else None
