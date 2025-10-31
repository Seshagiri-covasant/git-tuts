from ..utils.exceptions import QueryGenerationException
from sqlalchemy import inspect, text
from ..utils.prompt_loader import get_prompt
import logging
from typing import Dict, Any, Optional, List


class QueryGeneratorAgent:
    def __init__(self, llm, app_db_util=None, prompt_template=None, chatbot_db_util=None, chatbot_id: str | None = None, learning_cache: Optional[Dict] = None):
        self.llm = llm
        self.app_db_util = app_db_util  # For application DB (query execution)
        # For chatbot data (chat_bot.db)
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id
        self.learning_cache = learning_cache or {}
        self.query_patterns = self.learning_cache.get('query_patterns', {})
        self.successful_queries = self.learning_cache.get('successful_queries', [])
        self.failed_queries = self.learning_cache.get('failed_queries', [])
        if not prompt_template:
            raise ValueError(
                "No template provided. Please provide a template content.")
        self.prompt_template = prompt_template

    def _get_database_type(self):
        """Detect database type from the database URL."""
        if not self.app_db_util:
            return "sqlite"  # Default fallback

        db_url = str(self.app_db_util.db_engine.url)
        if 'bigquery://' in db_url:
            return "bigquery"
        elif 'postgresql' in db_url or 'postgres://' in db_url:
            return "postgresql"
        elif 'mysql' in db_url:
            return "mysql"
        elif 'mssql' in db_url:
            return "mssql"
        else:
            return "sqlite"

    def _get_actual_table_names(self):
        """Get actual table names from the database to prevent case sensitivity issues."""
        try:
            if not self.app_db_util:
                return []

            inspector = inspect(self.app_db_util.db_engine)
            # Respect selected schema for engines that support schemas (mssql/postgresql)
            selected_schema = self._get_selected_schema_name()
            try:
                if selected_schema:
                    table_names = inspector.get_table_names(schema=selected_schema)
                else:
                    table_names = inspector.get_table_names()
            except TypeError:
                # Some dialects don't accept schema kw; fallback
                table_names = inspector.get_table_names()
            return table_names
        except Exception as e:
            logging.info(f"Error getting table names: {e}")

            return []

    def _get_database_specific_instructions(self, db_type, clipped_context=None, question=None, state=None):
        """Get database-specific SQL generation instructions with unified parameter handling."""
        # Get actual table names
        actual_tables = self._get_actual_table_names()
        
        # Prepare common parameters
        import json as _json
        
        # Get schema context from clipped context if available
        schema_ctx = {}
        if clipped_context and isinstance(clipped_context, dict):
            schema_ctx = clipped_context.get("tables", {})
        
        # Get aggregation patterns and AI preferences from knowledge data
        knowledge_data = state.get("knowledge_data", {}) if state else {}
        if knowledge_data and isinstance(knowledge_data, dict):
            schema = knowledge_data.get("schema", {})
            if isinstance(schema, dict):
                aggregation_patterns = schema.get("aggregation_patterns", [])
                ai_preferences = schema.get("ai_preferences", [])
                
                if aggregation_patterns:
                    print(f"[QueryGenerator] Found {len(aggregation_patterns)} aggregation patterns")
                    for pattern in aggregation_patterns:
                        print(f"  - {pattern.get('name', 'Unknown')}: {pattern.get('keywords', [])}")
                else:
                    print("[QueryGenerator] No aggregation patterns found in schema")
                
                if ai_preferences:
                    print(f"[QueryGenerator] Found {len(ai_preferences)} AI preferences")
                    for preference in ai_preferences:
                        print(f"  - {preference.get('name', 'Unknown')}: {preference.get('value', 'No value')}")
                else:
                    print("[QueryGenerator] No AI preferences found in schema")
        
        # Prepare table list based on database type
        if db_type == "bigquery":
            table_list = ", ".join([f'`{table}`' for table in actual_tables]) if actual_tables else "No tables found"
        elif db_type == "mssql":
            table_list = ", ".join([f'[{table}]' for table in actual_tables]) if actual_tables else "No tables found"
        else:
            table_list = ", ".join([f'"{table}"' for table in actual_tables]) if actual_tables else "No tables found"
        
        # Parse project/dataset for BigQuery
        project = ""
        dataset = ""
        if db_type == "bigquery":
            try:
                url_str = str(self.app_db_util.db_engine.url) if self.app_db_util else ""
                if "bigquery://" in url_str:
                    remainder = url_str.split("bigquery://", 1)[1]
                    parts = remainder.split("/")
                    if len(parts) >= 2:
                        project = parts[0]
                        dataset = parts[1]
            except Exception:
                pass

        # Determine selected schema_name for dialects that support it (postgresql, mssql)
        selected_schema = None
        try:
            if self.chatbot_db_util and self.chatbot_id:
                cb = self.chatbot_db_util.get_chatbot(self.chatbot_id)
                selected_schema = (cb or {}).get("schema_name")
        except Exception:
            selected_schema = None

        # Generate instructions based on database type
        if db_type == "postgresql":
            return get_prompt(
                "sql_generation/postgresql_instructions.txt", 
                table_list=table_list,
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False),
                schema_name=selected_schema or ""
            )
        
        elif db_type == "bigquery":
            return get_prompt(
                "sql_generation/bigquery_instructions.txt",
                project=project or "",
                dataset=dataset or "",
                table_list=table_list or "",
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False),
                intent=question or ""
            )
        
        elif db_type == "mysql":
            return get_prompt(
                "sql_generation/mysql_instructions.txt",
                table_list=table_list,
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False)
            )
        elif db_type == "mssql":
            return get_prompt(
                "sql_generation/mssql_instructions.txt",
                table_list=table_list,
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False),
                schema_name=selected_schema or ""
            )
        else:
            # SQLite (default)
            return get_prompt(
                "sql_generation/sqlite_instructions.txt", 
                table_list=table_list,
                schema_context=_json.dumps(schema_ctx, ensure_ascii=False)
            )

    def _get_selected_schema_name(self) -> str | None:
        try:
            if self.chatbot_db_util and self.chatbot_id:
                cb = self.chatbot_db_util.get_chatbot(self.chatbot_id)
                return (cb or {}).get("schema_name")
        except Exception:
            return None
        return None

    def _qualify_table(self, db_type: str, table_name: str, schema_name: str | None) -> str:
        if not schema_name or db_type not in ("postgresql", "mssql"):
            return f'"{table_name}"' if db_type != "bigquery" else f'`{table_name}`'
        if db_type == "postgresql":
            return f'"{schema_name}"."{table_name}"'
        if db_type == "mssql":
            return f'[{schema_name}].[{table_name}]'
        return table_name

    def _ensure_schema_qualification(self, sql: str, db_type: str, schema_name: str | None) -> str:
        if not schema_name or db_type not in ("postgresql", "mssql"):
            return sql
        import re as _re
        def _qualify(match):
            kw = match.group(1)
            ident = match.group(2)
            rest = match.group(3) or ""
            # If already qualified or quoted with schema, leave
            if '.' in ident or ident.startswith('"') or ident.startswith('['):
                return f"{kw} {ident}{rest}"
            if db_type == "postgresql":
                qualified = f'"{schema_name}"."{ident}"'
            else:
                qualified = f'[{schema_name}].[{ident}]'
            return f"{kw} {qualified}{rest}"

        # Qualify identifiers in FROM and JOIN clauses when unqualified
        pattern = _re.compile(r"\b(FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)(\s+AS\b|\s+|$)", _re.IGNORECASE)
        sql = _re.sub(pattern, _qualify, sql)
        return sql

    def _extract_sql_from_response(self, response):
        """Extract clean SQL from LLM response, removing markdown fences and explanations."""
        try:
            # Convert response to string
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            # Remove markdown code fences
            import re
            import json as _json

            # Try to parse JSON-shaped outputs and extract { "sql": "..." }
            try:
                maybe_json_text = response_text.strip()
                if maybe_json_text.startswith('{') and maybe_json_text.endswith('}'):
                    obj = _json.loads(maybe_json_text)
                    if isinstance(obj, dict) and 'sql' in obj and isinstance(obj['sql'], str):
                        response_text = obj['sql']
            except Exception:
                pass

            # Remove ```sql and ``` markers
            response_text = re.sub(
                r'```sql\s*', '', response_text, flags=re.IGNORECASE)
            response_text = re.sub(
                r'```\s*$', '', response_text, flags=re.IGNORECASE)

            # Remove any leading/trailing whitespace
            response_text = response_text.strip()

            # Prefer the substring starting at the first SELECT keyword
            m = re.search(r'\bSELECT\b', response_text, flags=re.IGNORECASE)
            if m:
                response_text = response_text[m.start():]

            # Drop any leading narrator text like "Generated SQL:" or bullets before SELECT
            response_text = re.sub(r'^(Generated\s+SQL\s*:\s*)', '', response_text, flags=re.IGNORECASE)

            # Keep only up to the final semicolon if present; otherwise use whole
            semicolon_pos = response_text.rfind(';')
            if semicolon_pos != -1:
                candidate = response_text[:semicolon_pos + 1]
            else:
                candidate = response_text

            # Collapse excessive whitespace
            candidate = re.sub(r'\s+', ' ', candidate).strip()

            # If we still don't see a SELECT and FROM, fallback to best-effort token filter
            if not re.search(r'\bSELECT\b', candidate, flags=re.IGNORECASE):
                lines = response_text.split('\n')
                sql_lines = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('--'):
                        continue
                    if any(k in line.upper() for k in ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']):
                        sql_lines.append(line)
                if sql_lines:
                    candidate = ' '.join(sql_lines)

            final_sql = candidate.strip()

            # Final spacing normalization for glued tokens around major keywords
            KEYWORDS = (
                r"(SELECT|FROM|WHERE|GROUP\s+BY|HAVING|QUALIFY|ORDER\s+BY|LIMIT|WINDOW|"
                r"JOIN|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+OUTER\s+JOIN|CROSS\s+JOIN|ON|"
                r"AND|OR)"
            )
            final_sql = re.sub(rf"([A-Za-z0-9_`\.\)])({KEYWORDS})\\b", r"\1 \2", final_sql, flags=re.IGNORECASE)
            final_sql = re.sub(r",(\S)", r", \1", final_sql)

            return final_sql.strip()

        except Exception as e:
            logging.info(f"Error extracting SQL from response: {e}")
            # Fallback to original response
            if hasattr(response, 'content'):
                return response.content
            return str(response)

    def _build_aggregation_patterns_section(self, aggregation_patterns, question):
        """
        Build dynamic aggregation patterns section based on schema patterns and user question.
        """
        if not aggregation_patterns:
            return "No aggregation patterns configured in schema."
        
        # Find patterns that match the user question
        question_lower = question.lower() if question else ""
        matching_patterns = []
        
        for pattern in aggregation_patterns:
            keywords = pattern.get('keywords', [])
            if any(keyword.lower() in question_lower for keyword in keywords):
                matching_patterns.append(pattern)
        
        if not matching_patterns:
            return "No aggregation patterns match the current question."
        
        # Build the patterns section
        patterns_text = "MATCHING AGGREGATION PATTERNS:\n"
        for pattern in matching_patterns:
            patterns_text += f"\n- {pattern.get('name', 'Unknown Pattern')}:\n"
            patterns_text += f"  Keywords: {', '.join(pattern.get('keywords', []))}\n"
            patterns_text += f"  SQL Template: {pattern.get('sql_template', 'No template')}\n"
            patterns_text += f"  Example: {pattern.get('example_question', 'No example')}\n"
        
        patterns_text += "\nUse these patterns to generate appropriate SQL with proper placeholders replaced."
        return patterns_text

    def _build_ai_preferences_section(self, ai_preferences):
        """
        Build AI preferences section for the LLM prompt.
        """
        if not ai_preferences:
            return "No AI preferences configured in schema."
        
        preferences_text = "CONFIGURED AI PREFERENCES:\n"
        for preference in ai_preferences:
            if isinstance(preference, dict):
                name = preference.get('name', 'Unknown Preference')
                value = preference.get('value', 'No value')
                description = preference.get('description', '')
                
                preferences_text += f"\n- {name}: {value}\n"
                if description:
                    preferences_text += f"  Description: {description}\n"
        
        preferences_text += "\nUse these preferences to guide your SQL generation approach and style."
        return preferences_text

    def _learn_from_successful_query(self, question: str, sql: str, intent: Dict, schema_context: Dict):
        """Learn from successful query patterns for future adaptation."""
        try:
            pattern_key = self._generate_query_pattern_key(question, intent)
            
            if pattern_key not in self.query_patterns:
                self.query_patterns[pattern_key] = {
                    'question_patterns': [],
                    'sql_patterns': [],
                    'intent_patterns': [],
                    'success_count': 0,
                    'last_used': None
                }
            
            # Store the successful pattern
            self.query_patterns[pattern_key]['question_patterns'].append(question)
            self.query_patterns[pattern_key]['sql_patterns'].append(sql)
            self.query_patterns[pattern_key]['intent_patterns'].append(intent)
            self.query_patterns[pattern_key]['success_count'] += 1
            self.query_patterns[pattern_key]['last_used'] = question
            
            # Add to successful queries list
            self.successful_queries.append({
                'question': question,
                'sql': sql,
                'intent': intent,
                'timestamp': question  # Using question as timestamp placeholder
            })
            
            # Update learning cache
            self.learning_cache['query_patterns'] = self.query_patterns
            self.learning_cache['successful_queries'] = self.successful_queries
            
            print(f"[QueryGenerator] Learned from successful query pattern: {pattern_key}")
            
        except Exception as e:
            print(f"[QueryGenerator] Error learning from successful query: {e}")

    def _learn_from_failed_query(self, question: str, error: str, intent: Dict):
        """Learn from failed query patterns to avoid similar mistakes."""
        try:
            pattern_key = self._generate_query_pattern_key(question, intent)
            
            if pattern_key not in self.query_patterns:
                self.query_patterns[pattern_key] = {
                    'question_patterns': [],
                    'sql_patterns': [],
                    'intent_patterns': [],
                    'success_count': 0,
                    'failure_count': 0,
                    'last_used': None
                }
            
            # Track failure
            if 'failure_count' not in self.query_patterns[pattern_key]:
                self.query_patterns[pattern_key]['failure_count'] = 0
            self.query_patterns[pattern_key]['failure_count'] += 1
            
            # Add to failed queries list
            self.failed_queries.append({
                'question': question,
                'error': error,
                'intent': intent,
                'timestamp': question  # Using question as timestamp placeholder
            })
            
            # Update learning cache
            self.learning_cache['query_patterns'] = self.query_patterns
            self.learning_cache['failed_queries'] = self.failed_queries
            
            print(f"[QueryGenerator] Learned from failed query pattern: {pattern_key}")
            
        except Exception as e:
            print(f"[QueryGenerator] Error learning from failed query: {e}")

    def _generate_query_pattern_key(self, question: str, intent: Dict) -> str:
        """Generate a pattern key for learning cache."""
        try:
            # Create a key based on question structure and intent
            question_words = question.lower().split()
            intent_tables = intent.get('tables', [])
            intent_columns = intent.get('columns', [])
            
            # Create a pattern key
            pattern_parts = []
            pattern_parts.append(f"tables_{len(intent_tables)}")
            pattern_parts.append(f"columns_{len(intent_columns)}")
            
            # Add question type indicators
            if any(word in question_words for word in ['count', 'how many', 'number']):
                pattern_parts.append('count_query')
            if any(word in question_words for word in ['average', 'mean', 'avg']):
                pattern_parts.append('avg_query')
            if any(word in question_words for word in ['sum', 'total']):
                pattern_parts.append('sum_query')
            if any(word in question_words for word in ['group', 'by', 'breakdown']):
                pattern_parts.append('groupby_query')
            
            return "_".join(pattern_parts)
            
        except Exception as e:
            print(f"[QueryGenerator] Error generating pattern key: {e}")
            return "unknown_pattern"

    def _find_similar_successful_patterns(self, question: str, intent: Dict) -> List[Dict]:
        """Find similar successful query patterns for adaptation."""
        try:
            current_pattern_key = self._generate_query_pattern_key(question, intent)
            similar_patterns = []
            
            for pattern_key, pattern_data in self.query_patterns.items():
                if pattern_key == current_pattern_key:
                    continue
                
                # Calculate similarity based on pattern structure
                similarity_score = self._calculate_pattern_similarity(
                    current_pattern_key, pattern_key, question, intent, pattern_data
                )
                
                if similarity_score > 0.6:  # Threshold for similarity
                    similar_patterns.append({
                        'pattern_key': pattern_key,
                        'pattern_data': pattern_data,
                        'similarity_score': similarity_score
                    })
            
            # Sort by similarity score
            similar_patterns.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_patterns[:3]  # Return top 3 similar patterns
            
        except Exception as e:
            print(f"[QueryGenerator] Error finding similar patterns: {e}")
            return []

    def _calculate_pattern_similarity(self, current_key: str, pattern_key: str, question: str, intent: Dict, pattern_data: Dict) -> float:
        """Calculate similarity between current query and stored patterns."""
        try:
            similarity_score = 0.0
            
            # Compare pattern keys
            current_parts = current_key.split('_')
            pattern_parts = pattern_key.split('_')
            
            # Count matching parts
            matching_parts = 0
            for part in current_parts:
                if part in pattern_parts:
                    matching_parts += 1
            
            if len(current_parts) > 0:
                similarity_score += (matching_parts / len(current_parts)) * 0.4
            
            # Compare question structure
            current_words = set(question.lower().split())
            for stored_question in pattern_data.get('question_patterns', []):
                stored_words = set(stored_question.lower().split())
                word_overlap = len(current_words.intersection(stored_words))
                if len(current_words) > 0:
                    word_similarity = word_overlap / len(current_words)
                    similarity_score += word_similarity * 0.3
                    break  # Use first stored question for comparison
            
            # Compare intent structure
            current_tables = set(intent.get('tables', []))
            current_columns = set(intent.get('columns', []))
            
            for stored_intent in pattern_data.get('intent_patterns', []):
                stored_tables = set(stored_intent.get('tables', []))
                stored_columns = set(stored_intent.get('columns', []))
                
                table_overlap = len(current_tables.intersection(stored_tables))
                column_overlap = len(current_columns.intersection(stored_columns))
                
                if len(current_tables) > 0:
                    table_similarity = table_overlap / len(current_tables)
                    similarity_score += table_similarity * 0.15
                
                if len(current_columns) > 0:
                    column_similarity = column_overlap / len(current_columns)
                    similarity_score += column_similarity * 0.15
                
                break  # Use first stored intent for comparison
            
            return min(similarity_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            print(f"[QueryGenerator] Error calculating pattern similarity: {e}")
            return 0.0

    def _build_adaptive_sql_prompt(self, question: str, intent: Dict, clipped: Dict, db_type: str, 
                                 db_instructions: str, from_join_scaffold: str, 
                                 similar_patterns: List[Dict]) -> str:
        """Build an adaptive SQL generation prompt using learned patterns."""
        try:
            # Base prompt structure
            base_prompt = f"""You are an advanced SQL query generator with adaptive learning capabilities. Your task is to convert natural language questions into SQL queries using schema-aware patterns and learned query structures.

DATABASE TYPE: {db_type.upper()}
{db_instructions}

STRICT REQUIREMENTS:
- Use ONLY the tables and columns provided in the context
- If required tables/columns are not available, output exactly "NOT FOUND"
- Never reference tables/columns outside the provided context
- Preserve the FROM/JOIN SCAFFOLD exactly if provided

INTENT ANALYSIS:
Tables: {intent.get('tables', [])}
Columns: {intent.get('columns', [])}
Aggregations: {intent.get('aggregations', [])}
Filters: {intent.get('filters', [])}
Joins: {intent.get('joins', [])}
Order By: {intent.get('order_by', [])}
Date Range: {intent.get('date_range', [])}

AVAILABLE CONTEXT:
{clipped}

FROM/JOIN SCAFFOLD (MANDATORY TO KEEP UNCHANGED):
{from_join_scaffold if from_join_scaffold else '(no scaffold available)'}

QUESTION: {question}"""

            # Add learned patterns section if available
            if similar_patterns:
                patterns_section = "\n\nLEARNED PATTERNS (Use these as guidance):\n"
                for i, pattern in enumerate(similar_patterns, 1):
                    pattern_data = pattern['pattern_data']
                    patterns_section += f"\nPattern {i} (Similarity: {pattern['similarity_score']:.2f}):\n"
                    patterns_section += f"  Success Count: {pattern_data.get('success_count', 0)}\n"
                    patterns_section += f"  Failure Count: {pattern_data.get('failure_count', 0)}\n"
                    
                    # Show recent successful SQL patterns
                    recent_sqls = pattern_data.get('sql_patterns', [])[-2:]  # Last 2 SQLs
                    for j, sql in enumerate(recent_sqls, 1):
                        patterns_section += f"  Recent SQL {j}: {sql[:200]}...\n"
                
                base_prompt += patterns_section

            # Add adaptive instructions
            adaptive_instructions = """

ADAPTIVE INSTRUCTIONS:
1. Use the learned patterns as guidance for query structure and approach
2. Adapt successful patterns to the current question context
3. Avoid patterns that have high failure rates
4. Consider the schema metadata for optimal column selection
5. Use business patterns and AI preferences from the schema
6. Generate syntactically correct SQL with proper error handling

Generate the SQL query:"""

            return base_prompt + adaptive_instructions

        except Exception as e:
            print(f"[QueryGenerator] Error building adaptive prompt: {e}")
            # Fallback to basic prompt
            return f"""You are a SQL query generator. Generate a valid {db_type.upper()} SQL query for:

QUESTION: {question}
INTENT: {intent}
CONTEXT: {clipped}

Generate the SQL query:"""

    def run(self, state: Dict[str, Any], app_db_util=None, chatbot_db_util=None):
        try:
            # Use passed-in db utils if provided, else use instance
            app_db_util = app_db_util or self.app_db_util
            chatbot_db_util = chatbot_db_util or self.chatbot_db_util

            # Initialize variables at the beginning of the method
            aggregation_patterns = []
            ai_preferences = []
            question = None

            # Extract the latest human question (ignore system messages we added)
            for msg in reversed(state.get("messages", [])):
                # Handle LangChain message objects
                if hasattr(msg, "content") and hasattr(msg, "__class__"):
                    content = str(msg.content)
                    class_name = msg.__class__.__name__
                    
                    # Skip system messages we added (INTENT: and CLIPPED:)
                    if class_name == "SystemMessage" and (content.startswith("INTENT:") or content.startswith("CLIPPED:")):
                        continue
                    
                    # Look for HumanMessage
                    if class_name == "HumanMessage":
                        question = content
                        break
                
                # Handle dict messages (fallback)
                elif isinstance(msg, dict):
                    content = msg.get("content", "")
                    if msg.get("role") == "system" and (content.startswith("INTENT:") or content.startswith("CLIPPED:")):
                        continue
                    if msg.get("role") == "human" and "content" in msg:
                        question = msg["content"]
                        break
            
            # If still no question found, look for any non-system message
            if question is None:
                for msg in reversed(state.get("messages", [])):
                    if hasattr(msg, "content") and hasattr(msg, "__class__"):
                        class_name = msg.__class__.__name__
                        if class_name != "SystemMessage":
                            question = str(msg.content)
                            break
                    elif isinstance(msg, dict) and msg.get("role") != "system" and "content" in msg:
                        question = msg["content"]
                        break
            
            # Final fallback: try to get question from state directly
            if question is None:
                question = state.get("question") or state.get("user_question") or "No question found"

            # 🔍 ENHANCED LOGGING: Track what data is being processed
            print(f"\n{'='*80}")
            print(f"🔍 ADAPTIVE QUERY GENERATOR: Schema-Aware SQL Generation")
            print(f"{'='*80}")
            print(f"📝 User Question: {question}")
            print(f"📊 Learning Cache Size: {len(self.learning_cache)}")
            print(f"🎯 Query Patterns: {len(self.query_patterns)}")
            print(f"✅ Successful Queries: {len(self.successful_queries)}")
            print(f"❌ Failed Queries: {len(self.failed_queries)}")
            print(f"{'='*80}\n")

            # Detect database type
            db_type = self._get_database_type()
            # Defer building db_instructions until after we extract intent/clipped
            db_instructions = None

            # Recover intent and clipped context from system messages (get the LATEST ones)
            intent = {}
            clipped = {}
            
            # Simple approach: look for the last INTENT and CLIPPED messages
            messages = state.get("messages", [])
            
            # Find the last INTENT message
            for msg in reversed(messages):
                content_str = None
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str) and c.startswith("INTENT:"):
                        content_str = c
                elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                    c = getattr(msg, "content")
                    if c.startswith("INTENT:"):
                        content_str = c
                
                if content_str:
                    import json as _json
                    try:
                        intent = _json.loads(content_str[7:])
                        break
                    except Exception as e:
                        break
            
            # Find the last CLIPPED message
            for msg in reversed(messages):
                content_str = None
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str) and c.startswith("CLIPPED:"):
                        content_str = c
                elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                    c = getattr(msg, "content")
                    if c.startswith("CLIPPED:"):
                        content_str = c
                
                if content_str:
                    import json as _json
                    try:
                        clipped = _json.loads(content_str[8:])
                        break
                    except Exception as e:
                        break

            
            intent_tables = intent.get('tables') or []
            intent_columns = intent.get('columns') or []
            intent_aggregations = intent.get('aggregations') or []
            intent_text = f"INTENT TABLES: {intent_tables}\nINTENT COLUMNS: {intent_columns}\nINTENT AGGREGATIONS: {intent_aggregations}\nFILTERS: {intent.get('filters')}\nJOINS: {intent.get('joins')}\nORDER_BY: {intent.get('order_by')}\nDATE_RANGE: {intent.get('date_range')}"

            # Now that we have clipped context, build database-specific instructions
            if db_instructions is None:
                try:
                    db_instructions = self._get_database_specific_instructions(
                        db_type, 
                        clipped_context=clipped, 
                        question=question,
                        state=state
                    )
                except Exception as e:
                    logging.warning(f"Database prompt generation failed for {db_type}: {e}")
                    # Fallback to basic instructions
                    if db_type == "bigquery":
                        db_instructions = """You are an expert SQL generator for Google BigQuery (Standard SQL).

CRITICAL RULES:
1. Use backticks for all identifiers: `table`, `column`
2. Qualify ALL columns with table aliases: t.`column`
3. Use proper JOIN syntax: FROM table1 AS t1 INNER JOIN table2 AS t2 ON t1.`key` = t2.`key`
4. Put each clause on separate lines: SELECT, FROM, JOIN...ON, WHERE, GROUP BY, ORDER BY
5. Use BigQuery date functions: EXTRACT(YEAR FROM CAST(col AS DATE))
6. For SAP tables: EBAN(BANFN,BNFPO) ↔ EKPO(BANFN,BNFPO); EKPO.EBELN ↔ EKKO.EBELN
7. MAKE SURE TO GIVE PROPER SPACING BETWEEN WORDS IN THE SQL COMMAND. DO NOT MERGE WORDS TOGETHER AS IT WILL CAUSE ERRORS AND THE QUERY WONT EXECUTE. FOR EXAMPLE, 'EKKO.EBELNWHERE' IS WRONG, INSTEAD IT SHOULD BE 'EKKO.EBELN WHERE'. THIS IS VERY IMPORTANT.

Output ONLY the final SQL query, no explanations."""
                    else:
                        db_instructions = f"You are an expert SQL generator for {db_type.upper()}. Generate valid SQL queries with proper syntax and JOINs. Output only the SQL query."

            # Sample data is disabled per requirement
            selected_sample_text = ""
            
            # Build a deterministic, DB-agnostic FROM/JOIN scaffold to reduce malformed SQL
            def _build_from_join_scaffold() -> str:
                try:
                    if not intent_tables:
                        return ""
                    # Base table (preserve exact casing)
                    base_table = str(intent_tables[0])
                    selected_schema = self._get_selected_schema_name()
                    qualified_base = self._qualify_table(db_type, base_table, selected_schema)
                    scaffold_parts = [f"FROM {qualified_base} AS {base_table}"]
                    joins_spec = intent.get('joins') or []

                    # Helper to backtick qualified identifiers in ON strings
                    import re as _re
                    def _normalize_on(on_str: str) -> str:
                        if not isinstance(on_str, str):
                            return ""
                        # Keep as "Table.Column" without dialect-specific quoting
                        return _re.sub(r"\s+", " ", on_str.strip())

                    for j in joins_spec:
                        table_name = None
                        on_clause = None
                        join_keyword = "INNER JOIN"
                        if isinstance(j, dict):
                            # Support both {table1, table2, on} and {table, join_table, on}
                            table_name = j.get('table2') or j.get('join_table') or j.get('table') or j.get('table1')
                            on_clause = j.get('on')
                            if isinstance(j.get('type'), str):
                                # Optionally use provided join type
                                join_keyword = f"{j.get('type').strip().upper()} JOIN"
                        elif isinstance(j, str):
                            # Try to parse table names from a string like "EKPO.EBELN = EKKO.EBELN"
                            m = _re.search(r"\b([A-Za-z0-9_]+)\.[A-Za-z0-9_\s]+\s*=\s*([A-Za-z0-9_]+)\.[A-Za-z0-9_\s]+", j)
                            if m:
                                # Prefer the RHS table if it's different from base
                                rhs = m.group(2)
                                lhs = m.group(1)
                                table_name = rhs if rhs != base_table else lhs
                            on_clause = j
                        if table_name:
                            t = str(table_name)
                            qualified_join = self._qualify_table(db_type, t, selected_schema)
                            on_txt = _normalize_on(on_clause or "")
                            if on_txt:
                                scaffold_parts.append(f"{join_keyword} {qualified_join} AS {t} ON {on_txt}")
                            else:
                                # Leave an explicit placeholder ON to force the model to fill it
                                scaffold_parts.append(f"{join_keyword} {qualified_join} AS {t} ON /* FILL_JOIN_CONDITION */ 1=1")

                    return "\n".join(scaffold_parts)
                except Exception:
                    return ""

            from_join_scaffold = _build_from_join_scaffold()

            # Derive allowed tables; if clipped lacks tables, merge actual DB tables as a fallback (schema-scoped)
            allowed_tables = sorted(list((clipped.get('tables') or {}).keys()))
            if not allowed_tables:
                try:
                    allowed_tables = self._get_actual_table_names() or []
                except Exception:
                    allowed_tables = []
            allowed_tables_str = ", ".join([f'"{t}"' for t in allowed_tables]) if allowed_tables else ""

            # Determine relationship limit based on prompt size estimation
            relationships = clipped.get('relationships', [])
            # Start with 10 relationships, but reduce if needed
            relationship_limit = 10
            
            # Create clipped context with limited relationships
            clipped_limited = clipped.copy()
            clipped_limited['relationships'] = relationships[:relationship_limit]
            clipped_text = f"CLIPPED CONTEXT: {clipped_limited}"
            
            # Find similar successful patterns for adaptive learning
            similar_patterns = self._find_similar_successful_patterns(question, intent)
            
            # Special deterministic path: handle schema listing questions without LLM
            def _is_list_tables_question(q: str) -> bool:
                if not isinstance(q, str):
                    return False
                ql = q.lower()
                triggers = [
                    "what are the tables",
                    "list tables",
                    "show tables",
                    "available tables",
                    "tables in the database",
                ]
                return any(t in ql for t in triggers)

            if _is_list_tables_question(question):
                selected_schema = self._get_selected_schema_name()
                if db_type == "mssql":
                    base = "SELECT TABLE_SCHEMA AS SchemaName, TABLE_NAME AS TableName FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
                    if selected_schema:
                        base += " AND TABLE_SCHEMA = :schema"
                    base += " ORDER BY TABLE_SCHEMA, TABLE_NAME";
                    sql = base
                elif db_type == "postgresql":
                    base = "SELECT table_schema AS schema_name, table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema')"
                    if selected_schema:
                        base += " AND table_schema = :schema"
                    base += " ORDER BY table_schema, table_name";
                    sql = base
                else:
                    # Generic fallback
                    sql = "SELECT 1 WHERE 1=0"  # harmless noop

                print(f"[Query_Generator] Deterministic list-tables SQL: {sql}")
                return {
                    "messages": [sql],
                    "generated_sql": sql,
                    "sql_query": sql,
                    "sql": sql,
                    "query": sql,
                    "final_sql": sql,
                    "learning_cache": self.learning_cache
                }

            # Build adaptive prompt using learned patterns
            enhanced_prompt = self._build_adaptive_sql_prompt(
                question, intent, clipped_limited, db_type, db_instructions, 
                from_join_scaffold, similar_patterns
            )
            
            # Add the original template and additional sections
            enhanced_prompt += f"""

{self.prompt_template}

STRICT REQUIREMENTS:
- Use ONLY these tables: {allowed_tables_str if allowed_tables_str else 'None'}
- If required tables/columns are not available, output exactly "NOT FOUND"
- Never reference tables/columns outside the provided context
 - Preserve the FROM/JOIN SCAFFOLD exactly if provided (do not delete or alter JOIN order).

INTENT ANALYSIS:
{intent_text}

AVAILABLE CONTEXT:
{clipped_text}

 FROM/JOIN SCAFFOLD (MANDATORY TO KEEP UNCHANGED):
 {from_join_scaffold if from_join_scaffold else '(no scaffold available)'}

QUESTION: {question}

INSTRUCTIONS:
 1. Analyze the question and intent to understand what data is needed
 2. Use the provided FROM/JOIN SCAFFOLD verbatim (do not change it). If no scaffold shown, you must include a correct FROM base table and JOIN ... ON ... blocks.
 3. Add SELECT (with qualified columns), WHERE (if filters exist), GROUP BY (for any non-aggregated columns), ORDER BY, and row limiting as needed.
 4. Generate syntactically correct {db_type.upper()} SQL.
 5. Use proper table aliases for clarity and qualify all columns.
 6. Preserve identifiers' casing and spacing exactly as shown in context/samples.
 7. IMPORTANT: If INTENT AGGREGATIONS contains specific metric names, use those exact metric names in your SQL instead of raw column names.
 8. ROW LIMITING SYNTAX BY DATABASE:
    - For MSSQL: Use "ORDER BY column DESC OFFSET 0 ROWS FETCH NEXT N ROWS ONLY" instead of LIMIT
    - For MySQL/PostgreSQL: Use "LIMIT N"
    - For BigQuery: Use "LIMIT N"
    - For SQLite: Use "LIMIT N"

TOP QUERY HANDLING:
- When the question contains "top" , automatically add row limiting
- Default to TOP 10 if no specific number is mentioned.
- If a specific number is mentioned , use that number
- Always include ORDER BY with DESC for "top" queries to get the highest values first

DYNAMIC AGGREGATION PATTERNS:
{self._build_aggregation_patterns_section(aggregation_patterns, question)}

AI PREFERENCES:
{self._build_ai_preferences_section(ai_preferences)}

COMPLEX AGGREGATION PATTERNS:
- For percentage questions: Use COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () for percentages
- For "high" values: Use CTEs with AVG() to calculate thresholds, then filter WHERE column > threshold
- For comparisons (vs, versus): Use GROUP BY with the comparison column
- For breakdowns: Use GROUP BY with appropriate categorical columns

Generate the SQL query:"""

            # LOGGING: What data is being sent to LLM
            print(f"QUERY GENERATOR: Data being sent to LLM")
            print(f"{'='*60}")
            print(f"Prompt Length: {len(enhanced_prompt)} characters")
            print(f"Available Tables: {allowed_tables_str if allowed_tables_str else 'None'}")
            print(f"Relationship Limit: {relationship_limit}")
            print(f"Context Length: {len(clipped_limited)} characters")
            print(f"User Question: {question}")
            
            # Use invoke() for LLM call with timeout handling
            try:
                print(f"[Query_Generator] Calling LLM with prompt length: {len(enhanced_prompt)} (using {relationship_limit} relationships)")
                response = self.llm.invoke(enhanced_prompt)
                print(f"[Query_Generator] LLM response received")
            except Exception as e:
                logging.error(f"LLM call failed: {e}")
                return {"messages": ["Error generating SQL query. Please try again."]}

            # Extract and clean SQL from response
            print(f"\n{'='*60}")
            print(f"LLM RESPONSE ANALYSIS")
            print(f"{'='*60}")
            print(f"Raw LLM Response: {response}")
            print(f"Response Type: {type(response)}")
            if hasattr(response, 'content'):
                print(f"Response Content: {response.content}")
            print(f"{'='*60}\n")
            
            sql = self._extract_sql_from_response(response)
            
            print(f"\n{'='*60}")
            print(f"EXTRACTED SQL")
            print(f"{'='*60}")
            print(f"Extracted SQL: {sql}")
            print(f"SQL Length: {len(sql)} characters")
            print(f"{'='*60}\n")

            # Post-process: if scaffold exists but LLM omitted or broke it, inject/replace deterministically
            try:
                import re as _re
                if from_join_scaffold:
                    # If no FROM present, append scaffold
                    if not _re.search(r"\bFROM\b", sql, flags=_re.IGNORECASE):
                        sql = sql.strip().rstrip(';') + "\n" + from_join_scaffold
                    else:
                        # Replace the entire FROM... (until WHERE/GROUP/ORDER/HAVING/LIMIT or end) with scaffold
                        sql = _re.sub(r"\bFROM\b[\s\S]*?(?=\bWHERE\b|\bGROUP\b|\bORDER\b|\bHAVING\b|\bLIMIT\b|$)", from_join_scaffold, sql, flags=_re.IGNORECASE)
            except Exception:
                pass

            # Enforce schema qualification in final SQL as a last guard
            try:
                selected_schema = self._get_selected_schema_name()
                sql = self._ensure_schema_qualification(sql, db_type, selected_schema)
            except Exception:
                pass

            try:
                print(f"[Query_Generator] Generated SQL: {sql[:1000]}")
            except Exception:
                pass

            # AGENT THOUGHTS: Internal reasoning process
            agent_thoughts = self._generate_query_thoughts(question, sql, intent, clipped)

            # DECISION TRANSPARENCY: Structured decision trace
            decision_trace = self._build_query_decision_trace(question, sql, intent, clipped)

            # Learn from this successful query generation
            try:
                self._learn_from_successful_query(question, sql, intent, clipped_limited)
                print(f"[QueryGenerator] Successfully learned from query generation")
            except Exception as e:
                print(f"[QueryGenerator] Error learning from successful query: {e}")

            # CRITICAL FIX: Store SQL in multiple places for different agents to find
            return {
                "messages": [sql],
                "generated_sql": sql,
                "sql_query": sql,
                "sql": sql,  # Add this for query validator/executor
                "query": sql,  # Add this for query validator/executor
                "final_sql": sql,  # Add this for query validator/executor
                "agent_thoughts": agent_thoughts,
                "decision_trace": decision_trace,
                "learning_cache": self.learning_cache  # Pass learning cache to other agents
            }
        except Exception as e:
            # Learn from failed query generation
            try:
                self._learn_from_failed_query(question, str(e), intent)
                print(f"[QueryGenerator] Learned from failed query generation")
            except Exception as learn_error:
                print(f"[QueryGenerator] Error learning from failed query: {learn_error}")
            
            raise QueryGenerationException(e)
    
    def _generate_query_thoughts(self, question: str, sql: str, intent: Dict[str, Any], clipped: Dict[str, Any]) -> str:
        """Generate the agent's actual internal thoughts using LLM reasoning."""
        # Use the LLM to generate its own internal reasoning
        prompt = f"""
You are an AI agent that generates SQL queries from user questions.
Show your internal thought process as you create the SQL.

User Question: "{question}"

Intent Information:
Tables: {intent.get('tables', [])}
Columns: {intent.get('columns', [])}
Filters: {intent.get('filters', [])}

Generated SQL: {sql}

Your Task: Show your internal reasoning process as you decided how to generate this SQL.

Think step by step:
1. What do you notice about the user's question?
2. How do you decide which columns to SELECT?
3. How do you choose the FROM table?
4. How do you construct the WHERE clause?
5. What additional columns do you include and why?
6. How do you ensure the SQL is correct and efficient?

Show your actual thought process, not just the final result.
"""

        try:
            # Get the LLM to generate its own internal thoughts
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error generating internal thoughts: {e}"
    
    def _build_query_decision_trace(self, question: str, sql: str, intent: Dict, clipped: Dict) -> Dict:
        """Build structured decision trace for SQL generation."""
        import re
        
        # Parse SQL components
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE)
        from_match = re.search(r'FROM\s+(.*?)(?:\s+WHERE|\s+ORDER|\s+GROUP|\s*$)', sql, re.IGNORECASE)
        where_match = re.search(r'WHERE\s+(.*?)(?:\s+ORDER|\s+GROUP|\s*$)', sql, re.IGNORECASE)
        
        selected_columns = [col.strip() for col in select_match.group(1).split(',')] if select_match else []
        table_name = from_match.group(1).strip() if from_match else ""
        where_condition = where_match.group(1).strip() if where_match else ""
        
        trace = {
            "agent": "QueryGenerator",
            "question": question,
            "generated_sql": sql,
            "sql_components": {
                "selected_columns": selected_columns,
                "from_table": table_name,
                "where_condition": where_condition,
                "has_where": bool(where_match),
                "has_order_by": bool(re.search(r'ORDER\s+BY', sql, re.IGNORECASE)),
                "has_group_by": bool(re.search(r'GROUP\s+BY', sql, re.IGNORECASE))
            },
            "intent_mapping": {
                "intent_tables": intent.get('tables', []),
                "intent_columns": intent.get('columns', []),
                "intent_filters": intent.get('filters', []),
                "intent_aggregations": intent.get('aggregations', [])
            },
            "column_selection_reasons": {},
            "table_selection_reasons": {},
            "filter_construction_reasons": {},
            "additional_columns_added": [],
            "context_usage": {}
        }
        
        # Analyze column selection reasoning
        for col in selected_columns:
            if 'SPT_RowId' in col:
                trace["column_selection_reasons"][col] = {
                    "reason": "Primary key/identifier - essential for record identification",
                    "source": "Added for data integrity",
                    "relevance": "CRITICAL"
                }
            elif 'Overall_Risk_Score' in col:
                trace["column_selection_reasons"][col] = {
                    "reason": "Direct match to user's 'risk score' query",
                    "source": "Intent column",
                    "relevance": "CRITICAL"
                }
            elif 'AmountIncl_RC' in col:
                trace["column_selection_reasons"][col] = {
                    "reason": "Payment amount data - contextual information",
                    "source": "Added for context",
                    "relevance": "HIGH"
                }
            elif 'PaymentRunDate' in col:
                trace["column_selection_reasons"][col] = {
                    "reason": "Temporal data - time context for analysis",
                    "source": "Added for context",
                    "relevance": "MEDIUM"
                }
            else:
                trace["column_selection_reasons"][col] = {
                    "reason": "General data column",
                    "source": "Added for completeness",
                    "relevance": "LOW"
                }
        
        # Analyze table selection reasoning
        if table_name:
            trace["table_selection_reasons"][table_name] = {
                "reason": "Contains payment data with risk scores",
                "source": "Intent table",
                "schema_qualified": "[Analytics]" in table_name,
                "relevance": "CRITICAL"
            }
        
        # Analyze filter construction reasoning
        if where_condition:
            trace["filter_construction_reasons"][where_condition] = {
                "reason": "User specified 'above 10' condition",
                "source": "Intent filter",
                "logic": "Numeric threshold filtering",
                "implementation": "WHERE clause with comparison operator"
            }
        
        # Identify additional columns added beyond intent
        intent_columns = intent.get('columns', [])
        additional_columns = [col for col in selected_columns if col not in intent_columns]
        trace["additional_columns_added"] = additional_columns
        
        # Context usage analysis
        if clipped:
            trace["context_usage"] = {
                "clipped_available": True,
                "clipped_tables": clipped.get('tables', []),
                "clipped_columns": clipped.get('columns', []),
                "context_used": len(clipped) > 0
            }
        else:
            trace["context_usage"] = {
                "clipped_available": False,
                "context_used": False
            }
        
        return trace
