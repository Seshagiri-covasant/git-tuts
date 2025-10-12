import json
import os
from typing import Dict, Any, Optional
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.engine import Engine
import logging

try:
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False


class SchemaExtractor:
    """Extracts database schema information from various database types."""

    def __init__(self, db_url: str = None, db_type: str = None, credentials_json: Optional[str] = None, engine: Optional[Engine] = None, schema_name: Optional[str] = None, selected_tables: Optional[list] = None):
        """
        Initialize the schema extractor. Can be initialized with connection details OR an existing engine.

        Args:
            db_url: Database connection URL (if not providing an engine).
            db_type: Type of database (if not providing an engine).
            credentials_json: Service account JSON for BigQuery (if not providing an engine).
            engine: An existing SQLAlchemy engine to use for inspection.
        """
        if not engine and not (db_url and db_type):
            raise ValueError(
                "Must provide either a SQLAlchemy engine or both db_url and db_type.")

        self.db_url = db_url
        self.db_type = db_type.lower() if db_type else None
        self.credentials_json = credentials_json
        self.schema_name = schema_name
        self.selected_tables = selected_tables

        # Prioritize using the provided engine. If it's provided, we don't create a new connection.
        self.engine = engine
        self.temp_creds_file = None

        # If no engine is provided, this instance is responsible for creating and managing its own connection.
        if not self.engine:
            self._connect()

    def _connect(self):
        """Establish database connection if an engine was not provided during initialization."""
        # Local import to prevent circular dependency issues
        from config import create_database_engine, get_app_db_pool_config

        try:
            pool_config = get_app_db_pool_config()

            if self.db_type == 'bigquery':
                if not BIGQUERY_AVAILABLE:
                    raise ImportError(
                        "The 'google-cloud-bigquery' library is required for BigQuery connections. Please install it.")

                if self.credentials_json:
                    import tempfile
                    creds_data = json.loads(self.credentials_json)
                    # Use a non-deleting temp file to ensure it exists for the connection duration
                    fd, path = tempfile.mkstemp(suffix='.json', text=True)
                    with os.fdopen(fd, 'w') as tmp:
                        json.dump(creds_data, tmp)
                    self.temp_creds_file = path
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.temp_creds_file

            self.engine = create_database_engine(self.db_url, pool_config)

        except Exception as e:
            raise Exception(
                f"SchemaExtractor failed to connect to the database: {str(e)}")

    def __del__(self):
        """Cleanup temporary credentials file if one was created by this instance."""
        if self.temp_creds_file and os.path.exists(self.temp_creds_file):
            try:
                os.unlink(self.temp_creds_file)
            except Exception as e:
                logging.info(
                    f"Warning: Could not clean up temporary credentials file {self.temp_creds_file}: {e}")

    def extract_schema(self) -> Dict[str, Any]:
        """Extract complete database schema information using the initialized engine."""
        if not self.engine:
            raise Exception(
                "SchemaExtractor engine is not initialized. Cannot extract schema.")

        try:
            # Fast path for MSSQL: batch-fetch metadata for the selected schema
            try:
                dialect = str(self.engine.dialect.name).lower()
            except Exception:
                dialect = self.db_type or ""

            if dialect == "mssql" and self.schema_name:
                return self._extract_schema_mssql_batched()

            inspector = inspect(self.engine)

            schema_info = {
                "database_type": self.db_type or str(self.engine.dialect.name),
                "tables": [],
                "total_tables": 0,
                "total_columns": 0
            }

            # If a specific schema is provided, restrict to that; otherwise use default schema
            tables = inspector.get_table_names(schema=self.schema_name) if self.schema_name else inspector.get_table_names()
            
            if self.selected_tables:
                tables = [table for table in tables if table in self.selected_tables]

            schema_info["total_tables"] = len(tables)

            for table_name in tables:
                table_info = self._extract_table_info(inspector, table_name)
                schema_info["tables"].append(table_info)
                schema_info["total_columns"] += len(table_info["columns"])

            return schema_info

        except Exception as e:
            # Provide more context on BigQuery permission errors, which are common
            if "403 Forbidden" in str(e) and "bigquery" in str(self.engine.url):
                raise Exception(
                    f"Permission Denied for BigQuery. Please ensure the service account has the 'BigQuery Data Viewer' and 'BigQuery Metadata Viewer' IAM roles on the dataset. Original error: {e}")
            raise Exception(f"Failed to extract schema: {str(e)}")

    def _extract_schema_mssql_batched(self) -> Dict[str, Any]:
        """Efficiently extract schema for MSSQL by batching metadata queries per schema.

        Returns the same raw structure expected by the converter:
        {
          database_type: str,
          tables: [ { name, columns: [...], primary_keys: [...], foreign_keys: [...], indexes: [...], column_count } ],
          total_tables: int,
          total_columns: int
        }
        """
        schema = self.schema_name
        result: Dict[str, Any] = {
            "database_type": self.db_type or "mssql",
            "tables": [],
            "total_tables": 0,
            "total_columns": 0,
        }

        # Queries
        tables_sql = (
            """
            SELECT t.name AS table_name
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = :schema
            ORDER BY t.name
            """
        )

        columns_sql = (
            """
            SELECT t.name AS table_name,
                   c.name AS column_name,
                   ty.name AS data_type,
                   c.is_nullable,
                   c.column_id
            FROM sys.columns c
            JOIN sys.types ty ON c.user_type_id = ty.user_type_id
            JOIN sys.tables t ON c.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = :schema
            ORDER BY t.name, c.column_id
            """
        )

        pk_sql = (
            """
            SELECT t.name AS table_name,
                   c.name AS column_name,
                   ic.key_ordinal
            FROM sys.indexes i
            JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE i.is_primary_key = 1 AND s.name = :schema
            ORDER BY t.name, ic.key_ordinal
            """
        )

        fk_sql = (
            """
            SELECT fk.name AS fk_name,
                   src_t.name AS src_table,
                   src_c.name AS src_column,
                   tgt_t.name AS tgt_table,
                   tgt_c.name AS tgt_column,
                   fkc.constraint_column_id
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            JOIN sys.tables src_t ON fkc.parent_object_id = src_t.object_id
            JOIN sys.schemas src_s ON src_t.schema_id = src_s.schema_id
            JOIN sys.columns src_c ON src_c.object_id = fkc.parent_object_id AND src_c.column_id = fkc.parent_column_id
            JOIN sys.tables tgt_t ON fkc.referenced_object_id = tgt_t.object_id
            JOIN sys.schemas tgt_s ON tgt_t.schema_id = tgt_s.schema_id
            JOIN sys.columns tgt_c ON tgt_c.object_id = fkc.referenced_object_id AND tgt_c.column_id = fkc.referenced_column_id
            WHERE src_s.name = :schema
            ORDER BY src_t.name, fk.name, fkc.constraint_column_id
            """
        )

        indexes_sql = (
            """
            SELECT t.name AS table_name,
                   i.name AS index_name,
                   CAST(i.is_unique AS INT) AS is_unique,
                   c.name AS column_name,
                   ic.key_ordinal
            FROM sys.indexes i
            JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = :schema AND i.is_hypothetical = 0 AND i.name IS NOT NULL
            ORDER BY t.name, i.name, ic.key_ordinal
            """
        )

        try:
            with self.engine.connect() as conn:
                # Get table names and filter if selected_tables is provided
                table_names = [
                    row[0]
                    for row in conn.execute(text(tables_sql), {"schema": schema}).fetchall()
                    if not self.selected_tables or row[0] in self.selected_tables
                ]

                # Columns
                columns_rows = conn.execute(text(columns_sql), {"schema": schema}).fetchall()

                # PKs
                pk_rows = conn.execute(text(pk_sql), {"schema": schema}).fetchall()

                # FKs
                fk_rows = conn.execute(text(fk_sql), {"schema": schema}).fetchall()

                # Indexes
                index_rows = conn.execute(text(indexes_sql), {"schema": schema}).fetchall()

            # Organize columns per table
            columns_by_table: Dict[str, list] = {}
            for tname, col, dtype, is_nullable, _ord in columns_rows:
                cols = columns_by_table.setdefault(tname, [])
                cols.append({
                    "name": col,
                    "type": str(dtype),
                    "nullable": bool(is_nullable),
                    "default": None,
                })

            # Organize PKs per table
            pk_by_table: Dict[str, list] = {}
            for tname, col, _ord in pk_rows:
                pk_by_table.setdefault(tname, []).append(col)

            # Organize FKs per table, grouped by fk_name (multi-column FKs)
            from collections import defaultdict
            fk_grouped = defaultdict(lambda: defaultdict(lambda: {"constrained_columns": [], "referred_columns": [], "referred_table": None}))
            for fk_name, src_table, src_col, tgt_table, tgt_col, _ord in fk_rows:
                g = fk_grouped[src_table][fk_name]
                g["referred_table"] = tgt_table
                g["constrained_columns"].append(src_col)
                g["referred_columns"].append(tgt_col)

            fks_by_table: Dict[str, list] = {}
            for src_table, fks in fk_grouped.items():
                fks_by_table[src_table] = [
                    {
                        "constrained_columns": v["constrained_columns"],
                        "referred_table": v["referred_table"],
                        "referred_columns": v["referred_columns"],
                    }
                    for v in fks.values()
                ]

            # Organize indexes per table/index name
            idx_by_table = defaultdict(lambda: defaultdict(lambda: {"name": None, "columns": [], "unique": False}))
            for tname, idx_name, is_unique, col_name, _ord in index_rows:
                if not idx_name:
                    continue
                entry = idx_by_table[tname][idx_name]
                entry["name"] = idx_name
                entry["unique"] = bool(is_unique)
                entry["columns"].append(col_name)

            indexes_by_table: Dict[str, list] = {}
            for tname, idxs in idx_by_table.items():
                indexes_by_table[tname] = list(idxs.values())

            # Assemble tables
            result["total_tables"] = len(table_names)
            total_columns = 0
            for tname in table_names:
                cols = columns_by_table.get(tname, [])
                pks = pk_by_table.get(tname, [])
                # Set primary_key flag on columns
                for c in cols:
                    c["primary_key"] = c["name"] in pks
                fks = fks_by_table.get(tname, [])
                idx = indexes_by_table.get(tname, [])

                table_info = {
                    "name": tname,
                    "columns": cols,
                    "primary_keys": pks,
                    "foreign_keys": fks,
                    "indexes": idx,
                    "column_count": len(cols),
                }
                result["tables"].append(table_info)
                total_columns += len(cols)

            result["total_columns"] = total_columns
            return result
        except Exception as e:
            # Fallback to inspector path on any failure
            logging.error(f"MSSQL batched extraction failed, falling back to inspector: {e}")
            inspector = inspect(self.engine)
            schema_info = {
                "database_type": self.db_type or str(self.engine.dialect.name),
                "tables": [],
                "total_tables": 0,
                "total_columns": 0
            }
            tables = inspector.get_table_names(schema=self.schema_name) if self.schema_name else inspector.get_table_names()
            schema_info["total_tables"] = len(tables)
            for table_name in tables:
                table_info = self._extract_table_info(inspector, table_name)
                schema_info["tables"].append(table_info)
                schema_info["total_columns"] += len(table_info["columns"])
            return schema_info

    def _extract_table_info(self, inspector, table_name: str) -> Dict[str, Any]:
        """Extract detailed information for a specific table."""
        columns = inspector.get_columns(table_name, schema=self.schema_name)
        primary_keys = inspector.get_pk_constraint(
            table_name, schema=self.schema_name).get("constrained_columns", [])
        foreign_keys = inspector.get_foreign_keys(table_name, schema=self.schema_name)
        indexes = inspector.get_indexes(table_name, schema=self.schema_name)

        table_info = {
            "name": table_name,
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": col.get("default"),
                    "primary_key": col["name"] in primary_keys
                } for col in columns
            ],
            "primary_keys": primary_keys,
            "foreign_keys": [
                {
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"]
                } for fk in foreign_keys
            ],
            "indexes": [
                {
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx.get("unique", False)
                } for idx in indexes
            ],
            "column_count": len(columns)
        }
        return table_info

    def get_schema_summary(self) -> str:
        """Get a human-readable summary of the database schema."""
        schema = self.extract_schema()

        summary = f"Database Schema Summary ({schema['database_type'].upper()})\n"

        if schema["database_type"] == "bigquery" and self.db_url:
            if self.db_url.startswith("bigquery://"):
                parts = self.db_url.replace("bigquery://", "").split("/")
                if len(parts) == 2:
                    summary += f"Project ID: {parts[0]}\n"
                    summary += f"Dataset ID: {parts[1]}\n"

        summary += f"Total Tables: {schema['total_tables']}\n"
        summary += f"Total Columns: {schema['total_columns']}\n\n"

        for table in schema['tables']:
            summary += f"Table: {table['name']}\n"
            summary += f"  Columns ({table['column_count']}):\n"
            for column in table['columns']:
                pk_marker = " (PK)" if column['primary_key'] else ""
                nullable_marker = "" if column['nullable'] else " (NOT NULL)"
                summary += f"    - {column['name']}: {column['type']}{pk_marker}{nullable_marker}\n"

            if table['foreign_keys']:
                summary += f"  Foreign Keys:\n"
                for fk in table['foreign_keys']:
                    summary += f"    - ({', '.join(fk['constrained_columns'])}) -> {fk['referred_table']}({', '.join(fk['referred_columns'])})\n"

            summary += "\n"

        return summary

# Helper functions for backward compatibility and simpler external use


def extract_schema_from_db(db_url: str, db_type: str, credentials_json: Optional[str] = None) -> Dict[str, Any]:
    """Extract schema from database with optional BigQuery credentials."""
    extractor = SchemaExtractor(
        db_url=db_url, db_type=db_type, credentials_json=credentials_json)
    return extractor.extract_schema()


def get_schema_summary_from_db(db_url: str, db_type: str, credentials_json: Optional[str] = None) -> str:
    """Get schema summary from database with optional BigQuery credentials."""
    extractor = SchemaExtractor(
        db_url=db_url, db_type=db_type, credentials_json=credentials_json)
    return extractor.get_schema_summary()
