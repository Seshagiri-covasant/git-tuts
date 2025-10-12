"""
Schema Converter Utility
Converts raw database schemas to semantic schema models for enhanced LLM understanding.
"""

import re
from typing import Dict, Any, List
from datetime import datetime, timezone
from ..schemas.semantic_models import (
    DatabaseSchema, SemanticTable, SemanticColumn, SemanticRelationship,
    ColumnType, RelationshipType, ConnectionConfig
)


def map_sql_type_to_column_type(sql_type: str) -> ColumnType:
    """
    Maps SQL data types to our semantic ColumnType enum.
    
    Args:
        sql_type: Raw SQL type string from database
        
    Returns:
        ColumnType enum value
    """
    sql_type_lower = sql_type.lower()
    
    # PostgreSQL types
    if any(t in sql_type_lower for t in ['char', 'varchar', 'text', 'string']):
        return ColumnType.STRING
    elif any(t in sql_type_lower for t in ['int', 'integer', 'bigint', 'smallint', 'serial']):
        return ColumnType.INTEGER
    elif any(t in sql_type_lower for t in ['float', 'double', 'decimal', 'numeric', 'real']):
        return ColumnType.FLOAT
    elif any(t in sql_type_lower for t in ['bool', 'boolean']):
        return ColumnType.BOOLEAN
    elif any(t in sql_type_lower for t in ['date']):
        return ColumnType.DATE
    elif any(t in sql_type_lower for t in ['timestamp', 'datetime', 'time']):
        return ColumnType.DATETIME
    elif any(t in sql_type_lower for t in ['json', 'jsonb']):
        return ColumnType.JSON
    elif any(t in sql_type_lower for t in ['array', '[]']):
        return ColumnType.ARRAY
    
    # BigQuery types
    elif any(t in sql_type_lower for t in ['string', 'str']):
        return ColumnType.STRING
    elif any(t in sql_type_lower for t in ['int64', 'integer']):
        return ColumnType.INTEGER
    elif any(t in sql_type_lower for t in ['float64', 'float', 'numeric']):
        return ColumnType.FLOAT
    elif any(t in sql_type_lower for t in ['bool', 'boolean']):
        return ColumnType.BOOLEAN
    elif any(t in sql_type_lower for t in ['date']):
        return ColumnType.DATE
    elif any(t in sql_type_lower for t in ['datetime', 'timestamp']):
        return ColumnType.DATETIME
    
    # SQLite types
    elif any(t in sql_type_lower for t in ['text', 'varchar']):
        return ColumnType.STRING
    elif any(t in sql_type_lower for t in ['integer', 'int']):
        return ColumnType.INTEGER
    elif any(t in sql_type_lower for t in ['real', 'float']):
        return ColumnType.FLOAT
    elif any(t in sql_type_lower for t in ['blob']):
        return ColumnType.STRING  # Treat as string for now
    
    # Default fallback
    return ColumnType.STRING


def extract_foreign_key_columns(table_info: Dict[str, Any]) -> List[str]:
    """
    Extract column names that are foreign keys from table info.
    
    Args:
        table_info: Raw table information from schema extractor
        
    Returns:
        List of column names that are foreign keys
    """
    fk_columns = []
    for fk in table_info.get('foreign_keys', []):
        fk_columns.extend(fk.get('constrained_columns', []))
    return fk_columns


def convert_raw_schema_to_semantic(
    raw_schema: Dict[str, Any], 
    chatbot_id: str,
    db_url: str,
    db_type: str
) -> DatabaseSchema:
    """
    Convert raw database schema to semantic schema model.
    
    Args:
        raw_schema: Raw schema from SchemaExtractor
        chatbot_id: ID of the chatbot
        db_url: Database connection URL
        db_type: Type of database
        
    Returns:
        DatabaseSchema instance with semantic information
    """
    try:
        # Create connection config object
        connection_config = ConnectionConfig(
            db_url=db_url,
            db_type=db_type
        )
        
        # Convert tables
        semantic_tables = {}
        for raw_table in raw_schema.get('tables', []):
            # Get foreign key columns for this table
            fk_columns = extract_foreign_key_columns(raw_table)
            
            # Convert columns
            semantic_columns = {}
            for raw_col in raw_table.get('columns', []):
                semantic_col = SemanticColumn(
                    type=raw_col['type'],  # Use the raw SQL type
                    pk=raw_col.get('primary_key', False),
                    unique=raw_col.get('unique', False),
                    default=raw_col.get('default'),
                    # Legacy fields for backward compatibility
                    name=raw_col['name'],
                    display_name=raw_col['name'],
                    data_type=raw_col['type'],
                    is_primary_key=raw_col.get('primary_key', False),
                    is_foreign_key=raw_col['name'] in fk_columns,
                    synonyms=[],
                    metadata={}
                )
                semantic_columns[raw_col['name']] = semantic_col
            
            # Create semantic table
            semantic_table = SemanticTable(
                columns=semantic_columns,
                # Legacy fields for backward compatibility
                name=raw_table['name'],
                display_name=raw_table['name'],
                description=None,
                schema_name=raw_table.get('schema_name'),
                database_id=chatbot_id,
                business_context=None,
                row_count_estimate=None,
                metadata={}
            )
            semantic_tables[raw_table['name']] = semantic_table
        
        # Convert relationships (from foreign keys)
        semantic_relationships = []
        for raw_table in raw_schema.get('tables', []):
            for fk in raw_table.get('foreign_keys', []):
                # Find source and target tables
                source_table_name = raw_table['name']
                target_table_name = fk['referred_table']
                
                # Generate join SQL
                source_cols = fk.get('constrained_columns', [])
                target_cols = fk.get('referred_columns', [])
                
                if source_cols and target_cols:
                    # Create relationship using new clean structure
                    for source_col, target_col in zip(source_cols, target_cols):
                        semantic_relationship = SemanticRelationship(
                            from_field=f"{source_table_name}.{source_col}",
                            to=f"{target_table_name}.{target_col}",
                            # Legacy fields for backward compatibility
                            name=f"{source_table_name}_to_{target_table_name}",
                            description=f"Foreign key relationship from {source_table_name} to {target_table_name}",
                            source_table_id=source_table_name,
                            target_table_id=target_table_name,
                            source_columns=[source_col],
                            target_columns=[target_col],
                            relationship_type=RelationshipType.MANY_TO_ONE,
                            cardinality_ratio="N:1",
                            join_sql=f"{source_table_name}.{source_col} = {target_table_name}.{target_col}",
                            confidence_score=1.0,
                            metadata={}
                        )
                        semantic_relationships.append(semantic_relationship)
        
        # Create the complete semantic schema
        semantic_schema = DatabaseSchema(
            id=chatbot_id,
            display_name=f"Enhanced Schema for {chatbot_id}",
            connection_config=connection_config,
            tables=semantic_tables,
            relationships=semantic_relationships,
            metadata={
                "original_schema": raw_schema,
                "conversion_timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0"
            }
        )
        
        return semantic_schema
        
    except Exception as e:
        raise Exception(f"Failed to convert raw schema to semantic: {str(e)}")


def update_semantic_schema_from_raw(
    existing_semantic_schema: DatabaseSchema,
    raw_schema: Dict[str, Any]
) -> DatabaseSchema:
    """
    Update existing semantic schema with new raw schema data.
    Preserves user customizations while updating structure.
    
    Args:
        existing_semantic_schema: Current semantic schema with user customizations
        raw_schema: New raw schema from database
        
    Returns:
        Updated DatabaseSchema instance
    """
    try:
        # Create new semantic schema
        new_semantic_schema = convert_raw_schema_to_semantic(
            raw_schema,
            existing_semantic_schema.database_id,
            existing_semantic_schema.connection_config.get('db_url', ''),
            existing_semantic_schema.connection_config.get('db_type', '')
        )
        
        # Preserve user customizations from existing schema
        for existing_table in existing_semantic_schema.tables:
            # Find corresponding new table
            new_table = next((t for t in new_semantic_schema.tables if t.name == existing_table.name), None)
            if new_table:
                # Preserve user customizations
                new_table.display_name = existing_table.display_name
                new_table.description = existing_table.description
                new_table.business_context = existing_table.business_context
                new_table.synonyms = existing_table.synonyms
                new_table.metrics = existing_table.metrics
                new_table.metadata = existing_table.metadata
                
                # Preserve column customizations
                for existing_col in existing_table.columns:
                    new_col = next((c for c in new_table.columns if c.name == existing_col.name), None)
                    if new_col:
                        new_col.display_name = existing_col.display_name
                        new_col.description = existing_col.description
                        new_col.synonyms = existing_col.synonyms
                        new_col.metadata = existing_col.metadata
        
        # Preserve relationship customizations
        for existing_rel in existing_semantic_schema.relationships:
            new_rel = next((r for r in new_semantic_schema.relationships 
                           if r.source_table_id == existing_rel.source_table_id 
                           and r.target_table_id == existing_rel.target_table_id), None)
            if new_rel:
                new_rel.name = existing_rel.name
                new_rel.description = existing_rel.description
                new_rel.relationship_type = existing_rel.relationship_type
                new_rel.cardinality_ratio = existing_rel.cardinality_ratio
                new_rel.join_sql = existing_rel.join_sql
                new_rel.confidence_score = existing_rel.confidence_score
                new_rel.metadata = existing_rel.metadata
        
        # Preserve business metrics
        new_semantic_schema.metrics = existing_semantic_schema.metrics
        
        # Update metadata
        new_semantic_schema.metadata.update({
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "preserved_customizations": True
        })
        
        return new_semantic_schema
        
    except Exception as e:
        raise Exception(f"Failed to update semantic schema: {str(e)}")
