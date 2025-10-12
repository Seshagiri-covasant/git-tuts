from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime, timezone
import uuid

class SynonymWithSamples(BaseModel):
    """Represents a synonym with associated sample values."""
    synonym: str = Field(..., description="The synonym text")
    sample_values: List[str] = Field(default_factory=list, description="Sample values for this synonym")

# Enums
class ColumnType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"

class RelationshipType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"
    HIERARCHICAL = "hierarchical"

class AggregationType(str, Enum):
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    DISTINCT_COUNT = "distinct_count"

# Core Schema Models
class ForeignKeyReference(BaseModel):
    """Represents a foreign key reference to another table and column."""
    table: str = Field(..., description="Name of the referenced table")
    column: str = Field(..., description="Name of the referenced column")

class DateAlias(BaseModel):
    """Represents date alias configuration for time-based queries.
    
    This model matches the date_aliases structure in the JSON schema:
    - start: SQL expression for the start of the date range
    - end: SQL expression for the end of the date range
    - days_default: Default number of days for relative date ranges
    """
    start: Optional[str] = Field(default=None, description="SQL expression for the start of the date range")
    end: Optional[str] = Field(default=None, description="SQL expression for the end of the date range")
    days_default: Optional[int] = Field(default=None, description="Default number of days for relative date ranges")

class ConnectionConfig(BaseModel):
    """Represents database connection configuration.
    
    This model matches the connection_config structure in the JSON schema:
    - db_url: Database connection URL
    - db_type: Type of database (e.g., "postgresql", "mysql", "sqlite")
    """
    db_url: str = Field(..., description="Database connection URL")
    db_type: str = Field(..., description="Type of database (e.g., 'postgresql', 'mysql', 'sqlite')")

class TableAliases(BaseModel):
    """Represents table and column aliases for better LLM context."""
    table_aliases: Dict[str, str] = Field(default_factory=dict, description="Table name to alias mapping")
    column_aliases: Dict[str, Dict[str, str]] = Field(default_factory=dict, description="Table name to column aliases mapping")
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert aliases to JSON format."""
        result = {}
        if self.table_aliases:
            result["table_aliases"] = self.table_aliases
        if self.column_aliases:
            result["column_aliases"] = self.column_aliases
        return result

class OriginalSchema(BaseModel):
    """Represents original schema metadata.
    
    This model matches the original_schema structure in the metadata section:
    - database_type: Type of the original database
    - tables: List of table names
    - total_tables: Total number of tables
    - total_columns: Total number of columns
    """
    database_type: str = Field(..., description="Type of the original database")
    tables: List[str] = Field(default_factory=list, description="List of table names")
    total_tables: int = Field(default=0, description="Total number of tables")
    total_columns: int = Field(default=0, description="Total number of columns")

class SemanticColumn(BaseModel):
    """Represents a database column with semantic information.
    
    This model matches the new clean column structure:
    - type: Database data type (e.g., "integer", "varchar(100)")
    - pk: Boolean indicating if this is a primary key
    - fk: Foreign key reference object (optional)
    - unique: Boolean indicating if this column has unique constraint
    - default: Default value for the column
    """
    type: str = Field(..., description="Database data type (e.g., 'integer', 'varchar(100)', 'timestamp')")
    pk: bool = Field(default=False, description="True if this column is a primary key")
    fk: Optional[ForeignKeyReference] = Field(default=None, description="Foreign key reference if applicable")
    unique: bool = Field(default=False, description="True if this column has unique constraint")
    default: Optional[str] = Field(default=None, description="Default value for the column")
    
    # Legacy fields for backward compatibility
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="", description="Column name (legacy field)")
    display_name: str = Field(default="", description="Display name (derived from name)")
    description: Optional[str] = None
    data_type: str = Field(default="", description="Legacy field - use type instead")
    is_primary_key: bool = Field(default=False, description="Legacy field - use pk instead")
    is_foreign_key: bool = Field(default=False, description="Legacy field - use fk instead")
    synonyms: List[SynonymWithSamples] = Field(default_factory=list, description="Column-specific synonyms with sample values for LLM context")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __init__(self, **data):
        # Map legacy parsed fields to new ones before BaseModel init
        if 'relationship_type_legacy' in data and not data.get('relationship_type'):
            data['relationship_type'] = (
                data['relationship_type_legacy'].value
                if hasattr(data['relationship_type_legacy'], 'value')
                else data['relationship_type_legacy']
            )
        if 'cardinality_ratio_legacy' in data and not data.get('cardinality_ratio'):
            data['cardinality_ratio'] = data['cardinality_ratio_legacy']
        if 'join_sql_legacy' in data and not data.get('join_sql'):
            data['join_sql'] = data['join_sql_legacy']
        if 'confidence_score_legacy' in data and not data.get('confidence_score'):
            data['confidence_score'] = data['confidence_score_legacy']

        super().__init__(**data)
        # Auto-populate legacy fields for backward compatibility
        if not self.data_type:
            self.data_type = self.type
        if not self.display_name and self.name:
            self.display_name = self.name
        self.is_primary_key = self.pk
        self.is_foreign_key = self.fk is not None
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert the column to a dictionary matching the new clean JSON schema format."""
        # Convert synonyms to simple strings for columns
        def _syn_to_str(s: Any) -> str:
            try:
                # Pydantic v2 objects
                if hasattr(s, 'model_dump'):
                    data = s.model_dump()
                    return data.get("synonym", "")
                # Pydantic v1 objects
                if hasattr(s, 'dict'):
                    data = s.dict()
                    return data.get("synonym", "")
                # String fallback
                if isinstance(s, str):
                    return s
                # Already a mapping/dict
                if isinstance(s, dict):
                    return s.get("synonym", "")
            except Exception:
                pass
            # Last resort
            return str(s)

        result = {
            "type": self.type,
            "pk": self.pk,
            # Boolean FK flag similar to pk
            "fk": bool(self.fk) or self.is_foreign_key,
            "synonyms": [ _syn_to_str(s) for s in (self.synonyms or []) ],
            # New required column-level fields
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if self.description:
            result["description"] = self.description
        
        if self.fk:
            # Preserve the detailed FK reference alongside boolean fk flag
            result["fk_ref"] = {"table": self.fk.table, "column": self.fk.column}
        
        if self.unique:
            result["unique"] = self.unique
            
        if self.default:
            result["default"] = self.default
            
        return result

class SemanticTable(BaseModel):
    """Represents a database table with semantic information.
    
    This model matches the new clean table structure:
    - columns: Dictionary of column names to SemanticColumn objects
    - metrics: Dictionary of metric names to BusinessMetric objects (optional)
    """
    columns: Dict[str, SemanticColumn] = Field(default_factory=dict, description="Dictionary of column names to column definitions")
    metrics: Dict[str, 'BusinessMetric'] = Field(default_factory=dict, description="Dictionary of metric names to metric definitions")
    
    # Frontend fields for comprehensive schema capture
    synonyms: List[SynonymWithSamples] = Field(default_factory=list, description="Table-specific synonyms with sample values for LLM context")
    business_context: Optional[str] = Field(default=None, description="Business context and purpose of this table")
    row_count_estimate: Optional[int] = Field(default=None, description="Estimated number of rows in the table")
    
    # Legacy fields for backward compatibility
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="", description="Table name (legacy field)")
    display_name: str = Field(default="", description="Display name (derived from name)")
    description: Optional[str] = None
    schema_name: Optional[str] = Field(default=None, description="Database schema name (legacy field)")
    schema_legacy: Optional[str] = Field(default=None, description="Legacy field - use schema_name instead", alias="schema")
    database_id: str = Field(default="", description="Database identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-populate legacy fields for backward compatibility
        if not self.display_name and self.name:
            self.display_name = self.name
        if self.schema_name and not self.schema_legacy:
            self.schema_legacy = self.schema_name
        elif self.schema_legacy and not self.schema_name:
            self.schema_name = self.schema_legacy
    
    @property
    def schema(self) -> Optional[str]:
        """Backward compatibility property for schema field."""
        return self.schema_legacy
    
    @schema.setter
    def schema(self, value: Optional[str]) -> None:
        """Backward compatibility setter for schema field."""
        self.schema_legacy = value
        if not self.schema_name:
            self.schema_name = value
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert the table to a dictionary matching the new clean JSON schema format."""
        # Safely convert synonyms to plain dictionaries (keep sample_values for tables)
        def _syn_to_dict(s: Any) -> Dict[str, Any]:
            try:
                if hasattr(s, 'model_dump'):
                    return s.model_dump()
                if hasattr(s, 'dict'):
                    return s.dict()
                if isinstance(s, str):
                    return {"synonym": s, "sample_values": []}
                if isinstance(s, dict):
                    return {
                        "synonym": s.get("synonym", ""),
                        "sample_values": s.get("sample_values", [])
                    }
            except Exception:
                pass
            return {"synonym": str(s), "sample_values": []}

        result = {
            "columns": {name: col.to_json_dict() for name, col in self.columns.items()},
            "metrics": {name: metric.to_json_dict() for name, metric in self.metrics.items()} if self.metrics else {},
            "synonyms": [ _syn_to_dict(s) for s in (self.synonyms or []) ],
            "business_context": self.business_context,
            "row_count_estimate": self.row_count_estimate,
            # New required table-level fields
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "database_id": self.database_id,
            "schema_name": self.schema_name or self.schema_legacy,
            "table_id": self.id
        }
        
        if self.description:
            result["description"] = self.description
            
        return result

class SemanticRelationship(BaseModel):
    """Represents relationships between tables.
    
    This model matches the new clean relationship structure:
    - from: Source table.column in the relationship
    - to: Target table.column in the relationship
    """
    from_field: str = Field(..., description="Source table.column in the relationship")
    to: str = Field(default="", description="Target table.column in the relationship")
    
    # Additional semantic fields for comprehensive context
    synonyms: Optional[List[str]] = Field(default=None, description="Alternative names for this relationship")
    relationship_type: Optional[str] = Field(default=None, description="Type of relationship (e.g., one-to-many, many-to-many)")
    cardinality_ratio: Optional[str] = Field(default=None, description="Cardinality ratio description")
    join_sql: Optional[str] = Field(default=None, description="Example JOIN SQL for this relationship")
    confidence_score: Optional[float] = Field(default=None, description="Confidence score for this relationship")
    
    # Legacy fields for backward compatibility
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="", description="Relationship name (auto-generated)")
    description: Optional[str] = None
    left_table: str = Field(default="", description="Legacy field - use from_field instead")
    left_column: str = Field(default="", description="Legacy field - use from_field instead")
    right_table: str = Field(default="", description="Legacy field - use to instead")
    right_column: str = Field(default="", description="Legacy field - use to instead")
    source_table_id: str = Field(default="", description="Legacy field - use from_field instead")
    target_table_id: str = Field(default="", description="Legacy field - use to instead")
    source_columns: List[str] = Field(default_factory=list, description="Legacy field - use from_field instead")
    target_columns: List[str] = Field(default_factory=list, description="Legacy field - use to instead")
    relationship_type_legacy: Optional[RelationshipType] = Field(default=None, description="Legacy relationship type enum")
    cardinality_ratio_legacy: Optional[str] = None
    join_sql_legacy: Optional[str] = None
    confidence_score_legacy: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __init__(self, **data):
        """Initialize relationship with backward compatibility"""
        # Handle legacy field parsing
        if 'from' in data:
            # Parse legacy 'from' field into from_field
            from_data = data.pop('from')
            if isinstance(from_data, dict):
                # Extract table and column from legacy structure
                table = from_data.get('table', '')
                column = from_data.get('column', '')
                data['from_field'] = f"{table}.{column}" if table and column else ""
            else:
                data['from_field'] = str(from_data)
        
        if 'to' in data:
            # Parse legacy 'to' field
            to_data = data.pop('to')
            if isinstance(to_data, dict):
                # Extract table and column from legacy structure
                table = to_data.get('table', '')
                column = to_data.get('column', '')
                data['to'] = f"{table}.{column}" if table and column else ""
            else:
                data['to'] = str(to_data)
        
        # Parse legacy relationship fields if present
        if 'left_table' in data and 'left_column' in data:
            left_table = data.get('left_table', '')
            left_column = data.get('left_column', '')
            if left_table and left_column and 'from_field' not in data:
                data['from_field'] = f"{left_table}.{left_column}"
        
        if 'right_table' in data and 'right_column' in data:
            right_table = data.get('right_table', '')
            right_column = data.get('right_column', '')
            if right_table and right_column and 'to' not in data:
                data['to'] = f"{right_table}.{right_column}"
        
        # Handle legacy relationship type
        if 'relationship_type' in data:
            if isinstance(data['relationship_type'], str):
                # This is the new string field, keep it
                pass
            elif hasattr(data['relationship_type'], 'value'):
                # This is the legacy enum, convert to string and store in new field
                data['relationship_type'] = data['relationship_type'].value
                data['relationship_type_legacy'] = data['relationship_type']
            else:
                # Store in legacy field
                data['relationship_type_legacy'] = data['relationship_type']
                data['relationship_type'] = None
        
        # Handle legacy cardinality_ratio, join_sql, confidence_score (data-only, no self access before init)
        if 'cardinality_ratio' in data and data['cardinality_ratio'] is not None:
            data['cardinality_ratio_legacy'] = data.get('cardinality_ratio_legacy') or data['cardinality_ratio']
        
        if 'join_sql' in data and data['join_sql'] is not None:
            data['join_sql_legacy'] = data.get('join_sql_legacy') or data['join_sql']
        
        if 'confidence_score' in data and data['confidence_score'] is not None:
            data['confidence_score_legacy'] = data.get('confidence_score_legacy', data['confidence_score'])
        
        super().__init__(**data)
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert the relationship to a dictionary matching the new clean JSON schema format."""
        # Ensure synonyms are always a list of strings for relationships
        def _to_str(s: Any) -> str:
            if isinstance(s, str):
                return s
            if isinstance(s, dict):
                return s.get("synonym") or s.get("value") or str(s)
            # Pydantic objects
            if hasattr(s, 'model_dump'):
                d = s.model_dump()
                return d.get("synonym") or d.get("value") or str(d)
            if hasattr(s, 'dict'):
                d = s.dict()
                return d.get("synonym") or d.get("value") or str(d)
            return str(s)

        result = {
            "from": self.from_field,
            "to": self.to,
            "synonyms": [ _to_str(s) for s in (self.synonyms or []) ],
            "relationship_type": self.relationship_type,
            "cardinality_ratio": self.cardinality_ratio,
            "join_sql": self.join_sql,
            "confidence_score": self.confidence_score,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Only include non-None values
        return {k: v for k, v in result.items() if v is not None}

class BusinessMetric(BaseModel):
    """Represents calculated business metrics.
    
    This model matches the new clean metrics structure:
    - name: Display name of the metric
    - expression: SQL expression for calculating the metric
    - default_filters: List of default filters to apply (optional)
    """
    name: str = Field(..., description="Display name of the metric")
    expression: str = Field(..., description="SQL expression for calculating the metric")
    default_filters: List[str] = Field(default_factory=list, description="List of default filters to apply")
    
    # Additional semantic fields for comprehensive context
    description: Optional[str] = Field(default=None, description="Description of what this metric measures")
    aggregation_type: Optional[str] = Field(default=None, description="Type of aggregation (e.g., sum, count, average)")
    business_context: Optional[str] = Field(default=None, description="Business context and usage of this metric")
    
    # Legacy fields for backward compatibility
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Legacy field - auto-generated")
    display_name: str = Field(default="", description="Legacy field - use name instead")
    description: Optional[str] = None
    base_table: str = Field(default="", description="Legacy field - derived from context")
    sql_expression: str = Field(default="", description="Legacy field - use expression instead")
    aggregation_type: Optional[AggregationType] = None
    depends_on_tables: List[str] = Field(default_factory=list, description="Tables this metric depends on")
    depends_on_columns: List[str] = Field(default_factory=list, description="Columns this metric depends on")
    business_context: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-populate legacy fields for backward compatibility
        if not self.display_name:
            self.display_name = self.name
        if not self.sql_expression:
            self.sql_expression = self.expression
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert the metric to a dictionary matching the new clean JSON schema format."""
        result = {
            "name": self.name,
            "expression": self.expression,
            "default_filters": self.default_filters,
            "description": self.description,
            "aggregation_type": self.aggregation_type.value if self.aggregation_type else None,
            "business_context": self.business_context
        }
        
        # Only include non-None values
        return {k: v for k, v in result.items() if v is not None}

class DatabaseSchema(BaseModel):
    """Represents a complete database schema with semantic information.
    
    This model matches the new clean JSON schema structure:
    - id: Unique identifier for the schema
    - display_name: User-friendly name for the database
    - dialect: SQL dialect (e.g., "postgres", "mysql", "sqlite")
    - schema_prefix: Database schema prefix (e.g., "ecommerce")
    - connection_config: Database connection configuration
    - global_aliases: Table aliases for SQL queries
    - global_synonyms: Global synonyms dictionary
    - tables: Dictionary of table names to SemanticTable objects
    - relationships: List of relationships between tables
    - date_aliases: Date alias configurations
    - metadata: Additional metadata including original schema info
    - last_sync: Last synchronization timestamp
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the schema")
    display_name: str = Field(..., description="User-friendly name for the database")
    dialect: str = Field(default="postgres", description="SQL dialect (e.g., 'postgres', 'mysql', 'sqlite')")
    schema_prefix: Optional[str] = Field(default=None, description="Database schema prefix (e.g., 'ecommerce')")
    connection_config: ConnectionConfig = Field(..., description="Database connection configuration")

    aliases: TableAliases = Field(default_factory=TableAliases, description="Table and column aliases for LLM context")
    tables: Dict[str, SemanticTable] = Field(default_factory=dict, description="Dictionary of table names to table definitions")
    relationships: List[SemanticRelationship] = Field(default_factory=list, description="List of relationships between tables")
    date_aliases: Dict[str, DateAlias] = Field(default_factory=dict, description="Date alias configurations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata including original schema info")
    last_sync: Optional[datetime] = Field(default=None, description="Last synchronization timestamp")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    
    # Legacy fields for backward compatibility
    name: str = Field(default="", description="Legacy field - use display_name instead")
    database_id: str = Field(default="", description="Legacy field - use id instead")

    synonyms: Dict[str, List[str]] = Field(default_factory=dict, description="Legacy field - use global_synonyms instead")
    metrics: List[BusinessMetric] = Field(default_factory=list, description="Legacy field - metrics are now in tables")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-populate legacy fields for backward compatibility
        if not self.name:
            self.name = self.display_name
        if not self.database_id:
            self.database_id = self.id

    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert the database schema to a dictionary matching the new clean JSON schema format."""
        try:
            result = {
                "id": self.id,
                "display_name": self.display_name,
                "dialect": self.dialect,
                "connection_config": {
                    "db_url": self.connection_config.db_url,
                    "db_type": self.connection_config.db_type
                },
                "tables": {},
                "relationships": [],
                "metrics": [],
                "date_aliases": {},
                "metadata": self.metadata or {},
                "last_sync": self.last_sync.isoformat() if self.last_sync else None,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            }
            
            # Safely convert tables
            for name, table in self.tables.items():
                try:
                    result["tables"][name] = table.to_json_dict()
                except Exception as e:
                    print(f"Error converting table {name}: {e}")
                    result["tables"][name] = {"error": f"Failed to convert table: {str(e)}"}
            
            # Safely convert relationships
            for rel in self.relationships:
                try:
                    result["relationships"].append(rel.to_json_dict())
                except Exception as e:
                    print(f"Error converting relationship: {e}")
                    result["relationships"].append({"error": f"Failed to convert relationship: {str(e)}"})

            # Safely convert database-level metrics
            try:
                for m in (self.metrics or []):
                    try:
                        result["metrics"].append(m.to_json_dict())
                    except Exception as me:
                        print(f"Error converting metric: {me}")
                        result["metrics"].append({"error": f"Failed to convert metric: {str(me)}"})
            except Exception as e:
                print(f"Metrics conversion error: {e}")
            
            # Safely convert date aliases
            for k, v in self.date_aliases.items():
                try:
                    result["date_aliases"][k] = v.model_dump() if hasattr(v, 'model_dump') else v.dict()
                except Exception as e:
                    print(f"Error converting date alias {k}: {e}")
                    result["date_aliases"][k] = {"error": f"Failed to convert date alias: {str(e)}"}
            
            if self.schema_prefix:
                result["schema_prefix"] = self.schema_prefix
                
            # Include aliases for backward compatibility and frontend support
            if self.aliases:
                try:
                    result["aliases"] = self.aliases.to_json_dict()
                except Exception as e:
                    print(f"Error converting aliases: {e}")
                    result["aliases"] = {"error": f"Failed to convert aliases: {str(e)}"}

            return result
            
        except Exception as e:
            print(f"Critical error in to_json_dict: {e}")
            # Return a minimal valid structure
            return {
                "id": self.id or "unknown",
                "display_name": self.display_name or "Unknown Schema",
                "dialect": self.dialect or "postgres",
                "connection_config": {
                    "db_url": getattr(self.connection_config, 'db_url', ''),
                    "db_type": getattr(self.connection_config, 'db_type', 'postgresql')
                },
                "tables": {},
                "relationships": [],
                "date_aliases": {},
                "metadata": {},
                "error": f"Schema conversion failed: {str(e)}"
            }
    
    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> 'DatabaseSchema':
        """Create a DatabaseSchema instance from a JSON dictionary."""
        # Convert date_aliases back to DateAlias objects
        if 'date_aliases' in data:
            date_aliases = {}
            for k, v in data['date_aliases'].items():
                date_aliases[k] = DateAlias(**v)
            data['date_aliases'] = date_aliases
        
        # Convert connection_config back to ConnectionConfig object
        if 'connection_config' in data:
            data['connection_config'] = ConnectionConfig(**data['connection_config'])
        
        # Convert tables back to SemanticTable objects
        if 'tables' in data:
            tables = {}
            for table_name, table_data in data['tables'].items():
                # Convert columns back to SemanticColumn objects
                if 'columns' in table_data:
                    columns = {}
                    for col_name, col_data in table_data['columns'].items():
                        # Convert fk back to ForeignKeyReference object
                        if 'fk' in col_data:
                            col_data['fk'] = ForeignKeyReference(**col_data['fk'])
                        # Add the column name to the column data
                        col_data['name'] = col_name
                        columns[col_name] = SemanticColumn(**col_data)
                    table_data['columns'] = columns
                
                # Convert metrics back to BusinessMetric objects
                if 'metrics' in table_data:
                    metrics = {}
                    for metric_name, metric_data in table_data['metrics'].items():
                        metrics[metric_name] = BusinessMetric(**metric_data)
                    table_data['metrics'] = metrics
                
                # Add the table name to the table data
                table_data['name'] = table_name
                tables[table_name] = SemanticTable(**table_data)
            data['tables'] = tables
        
        # Convert relationships back to SemanticRelationship objects
        if 'relationships' in data:
            relationships = []
            for rel_data in data['relationships']:
                # Convert 'from' to 'from_field' for the model
                if 'from' in rel_data:
                    rel_data['from_field'] = rel_data.pop('from')
                relationships.append(SemanticRelationship(**rel_data))
            data['relationships'] = relationships
        
        # Convert datetime strings back to datetime objects
        if 'last_sync' in data and data['last_sync']:
            data['last_sync'] = datetime.fromisoformat(data['last_sync'].replace('Z', '+00:00'))
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if 'updated_at' in data:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        
        return cls(**data)

class EntityMapping(BaseModel):
    """Maps equivalent entities across different databases."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    canonical_name: str
    display_name: str
    description: Optional[str] = None
    mapped_tables: List[Dict[str, str]]
    mapped_columns: Dict[str, List[Dict[str, str]]]
    transformation_rules: Dict[str, str] = Field(default_factory=dict)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FederatedSemanticModel(BaseModel):
    """Represents a federated view across multiple databases."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    database_schemas: List[str]
    entity_mappings: List[EntityMapping]
    cross_database_relationships: List[SemanticRelationship]
    global_metrics: List[BusinessMetric]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# USAGE EXAMPLES AND DOCUMENTATION
# =============================================================================

"""
This module provides Pydantic models that match the JSON schema structure
defined in the cogni-bot project. The models are designed to:

1. Generate JSON in the exact format specified in json.txt
2. Maintain backward compatibility with existing code
3. Support frontend integration and updates
4. Provide proper serialization/deserialization methods

USAGE EXAMPLES:

1. Creating a DatabaseSchema from JSON:
   ```python
   import json
   from app.schemas.semantic_models import DatabaseSchema
   
   # Load JSON data
   with open('schema.json', 'r') as f:
       json_data = json.load(f)
   
   # Create DatabaseSchema instance
   schema = DatabaseSchema.from_json_dict(json_data)
   ```

2. Converting DatabaseSchema to JSON:
   ```python
   # Create schema instance
   schema = DatabaseSchema(
       display_name="E-commerce Database",
       dialect="postgres",
       connection_config=ConnectionConfig(
           db_url="postgresql://user:pass@localhost/db",
           db_type="postgresql"
       )
   )
   
   # Convert to JSON-compatible dictionary
   json_dict = schema.to_json_dict()
   
   # Save to file
   with open('output.json', 'w') as f:
       json.dump(json_dict, f, indent=2)
   ```

3. Creating individual components:
   ```python
   # Create a column with foreign key
   column = SemanticColumn(
       name="customer_id",
       data_type="integer",
       pk=False,
       fk=ForeignKeyReference(table="customers", column="customer_id"),
       synonyms=["client_id", "buyer_id"]
   )
   
   # Create a table
   table = SemanticTable(
       name="purchases",
       schema="ecommerce",
       synonyms=["orders", "transactions"],
       columns=[column]
   )
   
   # Create a relationship
   relationship = SemanticRelationship(
       left_table="purchases",
       left_column="customer_id",
       right_table="customers",
       right_column="customer_id"
   )
   
   # Create a metric
   metric = BusinessMetric(
       id="total_revenue",
       name="Total Revenue",
       base_table="purchases",
       expression="SUM(p.quantity * p.unit_price)",
       default_filters=["p.status = 'completed'"],
       synonyms=["total sales", "turnover"]
   )
   ```

BACKWARD COMPATIBILITY:

All models maintain backward compatibility by:
- Keeping legacy field names as optional fields
- Auto-populating legacy fields from new fields in __init__
- Providing both old and new field access patterns

FRONTEND INTEGRATION:

The models support frontend integration through:
- to_json_dict() methods that output the exact JSON format
- from_json_dict() class methods for parsing frontend data
- Proper handling of datetime serialization
- Support for all JSON schema fields

JSON SCHEMA COMPATIBILITY:

The models are designed to match the JSON structure in json.txt:
- DatabaseSchema matches the root JSON structure
- SemanticTable matches the tables array structure
- SemanticColumn matches the columns array structure
- SemanticRelationship matches the relationships array structure
- BusinessMetric matches the metrics array structure
- All supporting models (ForeignKeyReference, DateAlias, etc.) match their respective JSON structures
"""
