import json
import re
from typing import Any, Dict, List, Set, Tuple, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseLanguageModel


class AdvancedIntentPicker:
    """
    Advanced intent picker that combines conversational AI with sophisticated logic
    for perfect intent detection and super accuracy.
    """
    
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
        self.conversation_context = []
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method that uses advanced intent detection with conversational AI.
        Combines LLM understanding with sophisticated algorithms.
        """
        try:
            # Get the current user question and conversation context
            user_question = state.get('user_question', '')
            conversation_history = state.get('conversation_history', [])
            knowledge_data = state.get('knowledge_data', {})
            
            print(f"[AdvancedIntentPicker] Processing: {user_question}")
            print(f"[AdvancedIntentPicker] Conversation history: {len(conversation_history)} messages")
            print(f"[AdvancedIntentPicker] Knowledge data keys: {list(knowledge_data.keys()) if knowledge_data else 'None'}")
            # Handle both dict and list formats for schema tables
            schema_tables = knowledge_data.get('schema', {}).get('tables', {}) if knowledge_data else {}
            if isinstance(schema_tables, dict):
                table_count = len(schema_tables)
            elif isinstance(schema_tables, list):
                table_count = len(schema_tables)
            else:
                table_count = 0
            print(f"[AdvancedIntentPicker] Schema tables: {table_count}")
            
            # Build conversation context for the LLM
            conversation_context = self._build_conversation_context(conversation_history)
            
            # Step 1: Advanced intent analysis with LLM
            intent_analysis = self._analyze_user_intent_advanced(
                user_question, conversation_context, knowledge_data
            )
            
            # Step 2: Sophisticated post-processing
            enhanced_intent = self._enhance_intent_with_logic(
                intent_analysis, user_question, knowledge_data, conversation_context
            )
            
            # Step 3: Confidence scoring and validation
            confidence_scores = self._calculate_confidence_scores(
                enhanced_intent, user_question, knowledge_data
            )
            
            # Step 4: Schema-aware validation
            validated_intent = self._validate_intent_with_schema(
                enhanced_intent, knowledge_data
            )
            
            # Step 5: Post-selection validation - verify selected columns are best match
            final_validated_intent = self._validate_selection_quality(
                validated_intent, user_question, knowledge_data
            )
            
            print(f"[AdvancedIntentPicker] Final intent: {final_validated_intent}")
            print(f"[AdvancedIntentPicker] Confidence scores: {confidence_scores}")
            
            # AGENT THOUGHTS: Internal reasoning process
            agent_thoughts = self._generate_agent_thoughts(state.get('user_question', ''), final_validated_intent, knowledge_data, confidence_scores)
            
            return {
                **state,
                'intent': final_validated_intent,
                'confidence_scores': confidence_scores,
                'conversation_context': conversation_context,
                'agent_thoughts': agent_thoughts
            }
            
        except Exception as e:
            print(f"[AdvancedIntentPicker] Error: {e}")
            return {
                **state,
                'intent': {},
                'confidence_scores': {},
                'error': str(e)
            }
    
    def _build_conversation_context(self, conversation_history: List[Dict]) -> str:
        """
        Build a natural conversation context from the history.
        This helps the LLM understand what the user is referring to.
        """
        if not conversation_history:
            return "This is the start of our conversation."
        
        context_parts = []
        for i, message in enumerate(conversation_history[-10:]):  # Last 10 messages for context
            if message.get('role') == 'user':
                context_parts.append(f"User: {message.get('content', '')}")
            elif message.get('role') == 'assistant':
                context_parts.append(f"Assistant: {message.get('content', '')}")
        
        return "Previous conversation:\n" + "\n".join(context_parts)
    
    def _analyze_user_intent_advanced(self, user_question: str, conversation_context: str, knowledge_data: Dict) -> Dict:
        """
        Advanced intent analysis using LLM with sophisticated prompting.
        This is the core of the advanced intent detection.
        """
        
        # Create a comprehensive prompt for the LLM to understand intent
        system_prompt = """You are an advanced AI assistant that specializes in understanding database queries with perfect accuracy.
        
Your role is to:
1. Understand what the user wants to know from their question
2. Identify relevant database tables and columns with high precision
3. Extract any filters, aggregations, or sorting requirements accurately
4. Consider the conversation context to understand follow-up questions
5. Provide detailed reasoning for your selections
6. Be extremely accurate in your analysis

Guidelines:
- Understand the user's question in the context of our conversation
- Identify what database information they need with high precision
- Extract any specific requirements (filters, aggregations, etc.) accurately
- Consider if this is a follow-up to a previous question
- Provide detailed reasoning for your selections
- Be extremely accurate and thorough in your analysis

Remember: You should understand intent with perfect accuracy, just like ChatGPT does."""
        
        # Build knowledge overview for the LLM with semantic context
        knowledge_overview = self._build_knowledge_overview_with_semantic_context(knowledge_data, user_question)
        
        # Log basic info (reduced verbosity)
        print(f"[AdvancedIntentPicker] Processing question: {user_question[:100]}...")
        schema = knowledge_data.get('schema', {}) if 'schema' in knowledge_data else {}
        if schema:
            table_count = len(schema.get('tables', {}))
            print(f"[AdvancedIntentPicker] Schema: {table_count} tables, {len(knowledge_overview)} chars overview")
        
        user_prompt = f"""Conversation Context:
{conversation_context}
Current User Question: "{user_question}"
Available Database Schema with Business Context:
{knowledge_overview}

### YOUR TASK ###
You are an expert data analyst with deep semantic understanding. Your goal is to understand the user's intent and identify the exact Tables and columns needed to answer their question accurately.

### HOW TO SELECT COLUMNS ###
You must intelligently analyze the user's question and the available schema information. Use ALL available information:
- Column descriptions (when available) to understand purpose
- Column names and their semantic meaning when descriptions are missing
- Table context to understand relationships
- Question wording to understand intent

Your analysis should be thorough and intelligent. Think about:
- What is the user really asking for?
- What does each column represent semantically?
- Which column(s) best match the user's intent?
- Are there multiple columns that could work? If so, which is the MOST appropriate?

### SELECTION GUIDELINES ###
1. Analyze the question's semantic meaning deeply.
2. Match columns based on their true purpose (from description, name analysis, or context)
3. Select multiple columns if the question genuinely requires multiple pieces of information
4. Be precise - choose the BEST match, not all possible matches
5. Explain your reasoning clearly in the "reasoning" field
### FILTER FORMAT FOR FLAG COLUMNS ###


### JSON RESPONSE FORMAT ###
Respond with a JSON object in the following format. Do NOT include any comments or explanations outside the JSON structure.
{{
    "tables": ["table_name"],
    "columns": ["column_name_1", "column_name_2", "column_name_3"],
    "aggregations": ["aggregation_expression"],
    "filters": ["filter_expression"],
    "reasoning": "My detailed justification for selecting these columns based on their context and the user's question.",
    "confidence": {{
        "overall": 0.95,
        "columns": 0.7 
    }}
}}"""

        try:
            # Use the LLM to analyze the user's intent
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            #  LOGGING: Capture LLM's raw response and reasoning
            print(f" LLM RESPONSE ANALYSIS: Intent Picker")
            print(f" Raw LLM Response:")
            print(f"{response_text}")
            print(f" Response Length: {len(response_text)} characters")
            
            # Parse the LLM response
            try:
                # Clean the response text to remove markdown formatting and comments
                cleaned_response = response_text.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                # Remove JSON comments (// comments) that break JSON parsing
                cleaned_response = re.sub(r'//.*$', '', cleaned_response, flags=re.MULTILINE)
                
                intent_analysis = json.loads(cleaned_response)
                
                #  LOGGING: Show final parsed intent and column selection reasoning
                print(f" FINAL INTENT ANALYSIS: Column Selection Reasoning")
                print(f"{'='*80}")
                print(f" Parsed Intent:")
                print(f"  Tables: {intent_analysis.get('tables', [])}")
                print(f"  Columns: {intent_analysis.get('columns', [])}")
                print(f"  Aggregations: {intent_analysis.get('aggregations', [])}")
                print(f"  Reasoning: {intent_analysis.get('reasoning', 'No reasoning provided')}")
                print(f"  Confidence: {intent_analysis.get('confidence', {})}")
                
                # Analyze why specific columns were chosen
                aggregations = intent_analysis.get('aggregations', [])
                if aggregations:
                    print(f"\n AGGREGATION ANALYSIS:")
                    for agg in aggregations:
                        print(f"  Selected: {agg}")
                        # Check if using raw column names (uppercase with underscores) vs metrics (lowercase)
                        if agg.isupper() or (agg.count('_') > 0 and agg[0].isupper()):
                            print(f"     Using raw column name instead of metric")
                        elif agg.islower() or (agg.count('_') > 0 and agg[0].islower()):
                            print(f" Using metric name correctly")
                        else:
                            print(f"  Unknown aggregation pattern")
                
                print(f"{'='*80}\n")
                
                return intent_analysis
                
            except json.JSONDecodeError as json_error:
                print(f"[AdvancedIntentPicker] JSON parse error: {json_error}")
                print(f"[AdvancedIntentPicker] Attempting partial parsing...")
                
                # Attempt partial parsing - extract what we can
                partial_intent = {
                    "tables": [],
                    "columns": [],
                    "filters": [],
                    "aggregations": [],
                    "time_range": "",
                    "sorting": "",
                    "reasoning": "Partial parse due to JSON error",
                    "is_follow_up": False,
                    "follow_up_context": "",
                    "confidence": {"tables": 0.0, "columns": 0.0, "filters": 0.0, "aggregations": 0.0, "overall": 0.0}
                }
                
                # Try to extract JSON-like structures using regex
                try:
                    # Extract tables
                    tables_match = re.search(r'"tables"\s*:\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL)
                    if tables_match and tables_match.group(1):
                        tables_str = tables_match.group(1)
                        table_names = re.findall(r'"([^"]+)"', tables_str)
                        if table_names:
                            partial_intent["tables"] = table_names
                    
                    # Extract columns
                    columns_match = re.search(r'"columns"\s*:\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL)
                    if columns_match and columns_match.group(1):
                        columns_str = columns_match.group(1)
                        column_names = re.findall(r'"([^"]+)"', columns_str)
                        if column_names:
                            partial_intent["columns"] = column_names
                    
                    # Extract filters
                    filters_match = re.search(r'"filters"\s*:\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL)
                    if filters_match and filters_match.group(1):
                        filters_str = filters_match.group(1)
                        filter_exprs = re.findall(r'"([^"]+)"', filters_str)
                        if filter_exprs:
                            partial_intent["filters"] = filter_exprs
                    
                    # Extract reasoning if available
                    reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', response_text, re.IGNORECASE)
                    if reasoning_match and reasoning_match.group(1):
                        partial_intent["reasoning"] = reasoning_match.group(1)
                    
                    print(f"[AdvancedIntentPicker] Partial parse successful: tables={len(partial_intent['tables'])}, columns={len(partial_intent['columns'])}")
                    return partial_intent
                    
                except Exception as parse_error:
                    print(f"[AdvancedIntentPicker] Partial parse also failed: {parse_error}")
                    # Return empty intent as last resort
                    return partial_intent
                
        except Exception as e:
            print(f"[AdvancedIntentPicker] Error in LLM analysis: {e}")
            # Fallback: return basic intent structure
            return {
                "tables": [],
                "columns": [],
                "filters": [],
                "aggregations": [],
                "time_range": "",
                "sorting": "",
                "reasoning": f"Error: {e}",
                "is_follow_up": False,
                "follow_up_context": "",
                "confidence": {"tables": 0.0, "columns": 0.0, "filters": 0.0, "aggregations": 0.0, "overall": 0.0}
            }
    
    def _enhance_intent_with_logic(self, intent: Dict, user_question: str, knowledge_data: Dict, conversation_context: str) -> Dict:
        """
        Enhance intent with sophisticated logic and algorithms.
        This adds advanced processing on top of LLM analysis.
        """
        
        enhanced_intent = intent.copy()
        
        # 1. Schema-aware table selection
        if intent.get('tables'):
            enhanced_tables = self._enhance_table_selection(
                intent['tables'], user_question, knowledge_data
            )
            enhanced_intent['tables'] = enhanced_tables
        
        # 2. Column disambiguation and enhancement
        if intent.get('columns'):
            enhanced_columns = self._enhance_column_selection(
                intent['columns'], user_question, knowledge_data, conversation_context
            )
            enhanced_intent['columns'] = enhanced_columns
        
        # 3. Filter extraction and enhancement
        if intent.get('filters'):
            enhanced_filters = self._enhance_filter_extraction(
                intent['filters'], user_question, knowledge_data
            )
            enhanced_intent['filters'] = enhanced_filters
        
        # 4. Aggregation detection and enhancement
        if intent.get('aggregations'):
            enhanced_aggregations = self._enhance_aggregation_detection(
                intent['aggregations'], user_question, knowledge_data
            )
            enhanced_intent['aggregations'] = enhanced_aggregations
        
        # 5. Time range detection
        time_range = self._detect_time_range(user_question, conversation_context)
        if time_range:
            enhanced_intent['time_range'] = time_range
        
        # 6. Sorting detection
        sorting = self._detect_sorting(user_question, conversation_context)
        if sorting:
            enhanced_intent['sorting'] = sorting
        
        return enhanced_intent
    
    def _enhance_table_selection(self, tables: List[str], user_question: str, knowledge_data: Dict) -> List[str]:
        """
        Enhance table selection with sophisticated logic.
        FIXED: Check schema structure correctly.
        """
        enhanced_tables = []
        
        # Get schema tables from the correct structure
        schema = knowledge_data.get('schema', {})
        schema_tables = schema.get('tables', {})
        
        for table in tables:
            # Check if table exists in schema
            if table in schema_tables:
                enhanced_tables.append(table)
            else:
                # Try to find similar table names
                similar_tables = self._find_similar_tables(table, schema_tables)
                enhanced_tables.extend(similar_tables)
        
        return enhanced_tables
    
    def _enhance_column_selection(self, columns: List[str], user_question: str, knowledge_data: Dict, conversation_context: str) -> List[str]:
        """
        Enhance column selection with sophisticated disambiguation.
        FIXED: Check schema structure correctly.
        """
        enhanced_columns = []
        
        # Get schema tables from the correct structure
        schema = knowledge_data.get('schema', {})
        schema_tables = schema.get('tables', {})
        
        for column in columns:
            # Check if column exists in any table's columns
            column_exists = False
            for table_name, table_data in schema_tables.items():
                if isinstance(table_data, dict):
                    table_columns = table_data.get('columns', {})
                    if column in table_columns:
                        column_exists = True
                        break
            
            if column_exists:
                enhanced_columns.append(column)
            else:
                # Try to find similar column names
                similar_columns = self._find_similar_columns(column, schema_tables)
                enhanced_columns.extend(similar_columns)
        
        return enhanced_columns
    
    def _enhance_filter_extraction(self, filters: List[str], user_question: str, knowledge_data: Dict) -> List[str]:
        """
        Enhance filter extraction with sophisticated logic.
        """
        enhanced_filters = []
        
        for filter_expr in filters:
            # Enhance filter expression
            enhanced_filter = self._enhance_filter_expression(filter_expr, user_question, knowledge_data)
            enhanced_filters.append(enhanced_filter)
        
        return enhanced_filters
    
    def _enhance_aggregation_detection(self, aggregations: List[str], user_question: str, knowledge_data: Dict) -> List[str]:
        """
        Enhance aggregation detection with sophisticated logic.
        """
        enhanced_aggregations = []
        
        for agg in aggregations:
            # Enhance aggregation expression
            enhanced_agg = self._enhance_aggregation_expression(agg, user_question, knowledge_data)
            enhanced_aggregations.append(enhanced_agg)
        
        return enhanced_aggregations
    
    def _detect_time_range(self, user_question: str, conversation_context: str) -> Optional[str]:
        """
        Detect time range requirements with sophisticated logic.
        """
        time_patterns = [
            r'last\s+month',
            r'last\s+week',
            r'last\s+year',
            r'this\s+month',
            r'this\s+week',
            r'this\s+year',
            r'past\s+\d+\s+days',
            r'past\s+\d+\s+months',
            r'past\s+\d+\s+years'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, user_question.lower()):
                return pattern
        
        return None
    
    def _detect_sorting(self, user_question: str, conversation_context: str) -> Optional[str]:
        """
        Detect sorting requirements with sophisticated logic.
        """
        sorting_patterns = [
            r'highest',
            r'lowest',
            r'top\s+\d+',
            r'bottom\s+\d+',
            r'ascending',
            r'descending',
            r'order\s+by'
        ]
        
        for pattern in sorting_patterns:
            if re.search(pattern, user_question.lower()):
                return pattern
        
        return None
    
    def _calculate_confidence_scores(self, intent: Dict, user_question: str, knowledge_data: Dict) -> Dict:
        """
        Calculate sophisticated confidence scores for intent validation.
        FIXED: Use LLM's confidence scores first, then fallback to calculated ones.
        """
        confidence_scores = {}
        
        # FIXED: Use LLM's confidence scores if available
        llm_confidence = intent.get('confidence', {})
        
        # Table confidence - use LLM's confidence if available
        tables = intent.get('tables', [])
        if 'tables' in llm_confidence:
            confidence_scores['tables'] = llm_confidence['tables']
        else:
            table_confidence = self._calculate_table_confidence(tables, user_question, knowledge_data)
            confidence_scores['tables'] = table_confidence
        
        # Column confidence - use LLM's confidence if available
        columns = intent.get('columns', [])
        if 'columns' in llm_confidence:
            confidence_scores['columns'] = llm_confidence['columns']
        else:
            column_confidence = self._calculate_column_confidence(columns, user_question, knowledge_data)
            confidence_scores['columns'] = column_confidence
        
        # Filter confidence - use LLM's confidence if available
        filters = intent.get('filters', [])
        if 'filters' in llm_confidence:
            confidence_scores['filters'] = llm_confidence['filters']
        else:
            filter_confidence = self._calculate_filter_confidence(filters, user_question, knowledge_data)
            confidence_scores['filters'] = filter_confidence
        
        # Aggregation confidence - use LLM's confidence if available
        aggregations = intent.get('aggregations', [])
        if 'aggregations' in llm_confidence:
            confidence_scores['aggregations'] = llm_confidence['aggregations']
        else:
            agg_confidence = self._calculate_aggregation_confidence(aggregations, user_question, knowledge_data)
            confidence_scores['aggregations'] = agg_confidence
        
        # Overall confidence - use LLM's overall confidence if available
        if 'overall' in llm_confidence:
            confidence_scores['overall'] = llm_confidence['overall']
        else:
            # Avoid division by zero
            if confidence_scores:
                overall_confidence = sum(confidence_scores.values()) / len(confidence_scores)
                confidence_scores['overall'] = overall_confidence
            else:
                confidence_scores['overall'] = 0.0
        
        print(f"[AdvancedIntentPicker] Confidence calculation: Using LLM confidence: {bool(llm_confidence)}, Final scores: {confidence_scores}")
        
        return confidence_scores
    
    def _validate_intent_with_schema(self, intent: Dict, knowledge_data: Dict) -> Dict:
        """
        Validate intent against available schema with intelligent column selection.
        ACTUALLY validates that tables/columns exist in schema and filters invalid selections.
        """
        validated_intent = intent.copy()
        
        # Get schema
        schema = knowledge_data.get('schema', {})
        schema_tables = schema.get('tables', {})
        
        # VALIDATE TABLES: Check if selected tables exist in schema
        selected_tables = intent.get('tables', [])
        if selected_tables:
            validated_tables = []
            for table in selected_tables:
                if table in schema_tables:
                    validated_tables.append(table)
                    print(f"[AdvancedIntentPicker] Schema validation: Table '{table}' exists in schema ✓")
                else:
                    # Try to find similar table names
                    similar_tables = self._find_similar_tables(table, schema_tables)
                    if similar_tables:
                        validated_tables.extend(similar_tables)
                        print(f"[AdvancedIntentPicker] Schema validation: Table '{table}' not found, using similar: {similar_tables}")
                    else:
                        print(f"[AdvancedIntentPicker] Schema validation: Table '{table}' NOT FOUND in schema ✗")
            if validated_tables:
                validated_intent['tables'] = validated_tables
            else:
                # Fail fast: if no valid tables found, log error and keep empty list
                print(f"[AdvancedIntentPicker] WARNING: No valid tables found after validation. Selected tables: {selected_tables}")
                validated_intent['tables'] = []
        
        # VALIDATE COLUMNS: Check if selected columns exist in the selected tables
        selected_columns = intent.get('columns', [])
        if selected_columns and validated_intent.get('tables'):
            validated_columns = []
            # Build set of all valid column names from selected tables (ONCE, outside loop)
            valid_columns = set()
            for table_name in validated_intent.get('tables', []):
                if table_name in schema_tables:
                    table_data = schema_tables[table_name]
                    if isinstance(table_data, dict):
                        table_columns = table_data.get('columns', {})
                        if isinstance(table_columns, dict):
                            valid_columns.update(table_columns.keys())
            
            # Create schema subset once (outside loop) for efficiency
            schema_subset = {t: schema_tables[t] for t in validated_intent.get('tables', []) if t in schema_tables}
            
            # Validate each selected column
            for column in selected_columns:
                if column in valid_columns:
                    validated_columns.append(column)
                    print(f"[AdvancedIntentPicker] Schema validation: Column '{column}' exists in selected tables ✓")
                else:
                    # Try to find similar column names in selected tables
                    similar_columns = self._find_similar_columns(column, schema_subset)
                    if similar_columns:
                        validated_columns.extend(similar_columns)
                        print(f"[AdvancedIntentPicker] Schema validation: Column '{column}' not found, using similar: {similar_columns}")
                    else:
                        print(f"[AdvancedIntentPicker] Schema validation: Column '{column}' NOT FOUND in selected tables ✗")
            
            if validated_columns:
                validated_intent['columns'] = validated_columns
            else:
                # Fail fast: if no valid columns found, log error and keep empty list
                print(f"[AdvancedIntentPicker] WARNING: No valid columns found after validation. Selected columns: {selected_columns}")
                validated_intent['columns'] = []
        
        # Preserve filters and aggregations (no schema validation needed for these)
        if 'filters' in intent and intent['filters']:
            validated_intent['filters'] = intent['filters']
        
        if 'aggregations' in intent and intent['aggregations']:
            validated_intent['aggregations'] = intent['aggregations']
        
        return validated_intent

    def _validate_selection_quality(self, intent: Dict, user_question: str, knowledge_data: Dict) -> Dict:
        """
        Post-selection validation: Ask LLM to verify if selected columns are the best match.
        This ensures the LLM double-checks its own work intelligently.
        """
        selected_tables = intent.get('tables', [])
        selected_columns = intent.get('columns', [])
        
        if not selected_columns or not selected_tables:
            return intent
        
        # Get schema context for selected tables
        schema = knowledge_data.get('schema', {})
        schema_tables = schema.get('tables', {})
        
        # Build context of selected columns and alternatives
        columns_context = []
        for table_name in selected_tables:
            if table_name in schema_tables:
                table_data = schema_tables[table_name]
                columns = table_data.get('columns', {})
                for col_name, col_data in columns.items():
                    if isinstance(col_data, dict):
                        is_selected = col_name in selected_columns
                        desc = col_data.get('description', '')
                        context_parts = [f"Column: {col_name}"]
                        if desc:
                            context_parts.append(f"Description: {desc}")
                        if is_selected:
                            context_parts.append("[SELECTED]")
                        columns_context.append(" | ".join(context_parts))
        
        validation_prompt = f"""You previously selected these columns for the user's question: "{user_question}"

SELECTED COLUMNS: {selected_columns}

AVAILABLE COLUMNS IN SELECTED TABLES:
{"\n".join(columns_context[:50])}

### VALIDATION TASK ###
**CRITICAL**: Only suggest corrections if the selection is OBVIOUSLY WRONG or makes the query IMPOSSIBLE to execute.
If the selection can answer the question (even if you think more columns would be "better"), APPROVE IT.

**APPROVE the selection if:**
- The selected columns can answer the question.
- The selection matches what the user is asking for.

**ONLY correct if:**
- Selected columns are completely irrelevant to the question
- Selected columns would cause a SQL error (wrong column names)

**Default to APPROVING** - be very conservative.

Respond with JSON:
{{
    "are_selected_columns_best": true/false,
    "reasoning": "Brief explanation",
    "corrected_columns": ["column_name_1", "column_name_2"],
    "confidence": {{
        "overall": 0.0-1.0,
        "columns": 0.0-1.0
    }}
}}"""

        try:
            messages = [
                SystemMessage(content="You are a quality validator. Your role is to APPROVE selections that can answer the question, not to 'improve' them. Only reject if selection is clearly wrong or would cause errors."),
                HumanMessage(content=validation_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Parse validation response
            import re
            cleaned_response = response_text.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            cleaned_response = re.sub(r'//.*$', '', cleaned_response, flags=re.MULTILINE)
            
            validation_result = json.loads(cleaned_response)
            
            # If validation suggests corrections, use them (but only if they exist in schema)
            if not validation_result.get('are_selected_columns_best', True):
                corrected_columns = validation_result.get('corrected_columns', selected_columns)
                # Validate corrected columns exist in schema
                valid_columns = set()
                for table_name in selected_tables:
                    if table_name in schema_tables:
                        table_data = schema_tables[table_name]
                        table_columns = table_data.get('columns', {})
                        if isinstance(table_columns, dict):
                            valid_columns.update(table_columns.keys())
                
                validated_corrected = [c for c in corrected_columns if c in valid_columns]
                if validated_corrected:
                    print(f"[AdvancedIntentPicker] Selection quality validation: Original={selected_columns}, Corrected={validated_corrected}")
                    print(f"[AdvancedIntentPicker] Validation reasoning: {validation_result.get('reasoning', 'No reasoning provided')}")
                    intent['columns'] = validated_corrected
                else:
                    print(f"[AdvancedIntentPicker] Selection quality validation: Correction suggested but columns not in schema, keeping original")
            else:
                print(f"[AdvancedIntentPicker] Selection quality validation: Selected columns verified as best match ✓")
                
        except Exception as e:
            print(f"[AdvancedIntentPicker] Selection quality validation error: {e}, keeping original selection")
        
        return intent
    
    def _build_knowledge_overview_with_semantic_context(self, knowledge_data: Dict[str, Any], question: str) -> str:
        """
        Build a comprehensive schema overview with business context for description-driven reasoning.
        This helps the LLM understand column descriptions and business context to make informed decisions.
        """
        if not knowledge_data or 'schema' not in knowledge_data:
            return "No database schema information available."
        
        # Build natural schema overview from actual schema data
        schema = knowledge_data.get('schema', {})
        tables = schema.get('tables', {})
        
        # Handle both dict and list formats for tables
        if isinstance(tables, dict):
            tables_list = tables
        elif isinstance(tables, list):
            tables_list = {table.get('name', f'table_{i}'): table for i, table in enumerate(tables)}
        else:
            tables_list = {}
        
        overview_parts = ["Available Database Schema with Business Context:"]
        
        # Add database-level metrics if available and relevant to the question
        if 'metrics' in schema and schema['metrics']:
            question_lower = question.lower() if question else ""
            metrics_keywords = ['average', 'avg', 'sum', 'count', 'total', 'maximum', 'max', 'minimum', 'min', 'metric', 'score', 'rate', 'ratio', 'percentage', '%']
            
            if any(keyword in question_lower for keyword in metrics_keywords):
                overview_parts.append("\nAvailable Database Metrics:")
                for metric in schema['metrics']:
                    if isinstance(metric, dict):
                        metric_name = metric.get('name', 'Unknown')
                        metric_expression = metric.get('expression', 'Unknown')
                        overview_parts.append(f"  - {metric_name}: {metric_expression}")
                    else:
                        overview_parts.append(f"  - {metric}")
        
        for table_name, table_data in tables_list.items():
            if isinstance(table_data, dict):
                columns = table_data.get('columns', {})
                overview_parts.append(f"\n{table_name}:")
                
                if isinstance(columns, dict):
                    for col_name, col_data in columns.items():
                        if isinstance(col_data, dict):
                            col_type = col_data.get('type', col_data.get('data_type', 'Unknown'))
                            
                            # Build comprehensive context information
                            context_parts = []
                            
                            # Description (primary business context)
                            description = col_data.get('description', '')
                            if description:
                                context_parts.append(f"Description: \"{description}\"")
                            
                            # Business terms (alternative terms)
                            business_terms = col_data.get('business_terms', [])
                            if business_terms:
                                context_parts.append(f"Business Terms: {business_terms}")
                            
                            # Use cases (typical usage scenarios)
                            use_cases = col_data.get('use_cases', [])
                            if use_cases:
                                context_parts.append(f"Typical Use Cases: {use_cases}")
                            
                            # Build the context string
                            context_str = " | ".join(context_parts) if context_parts else "No additional context"
                            
                            # Format: column_name (type) - CONTEXT: Description | Business Terms | Use Cases
                            overview_parts.append(f"  - {col_name} ({col_type})")
                            overview_parts.append(f"    - CONTEXT: {context_str}")
        
        return "\n".join(overview_parts)
    
    # Helper methods for sophisticated logic
    def _find_similar_tables(self, table: str, schema_tables: Dict) -> List[str]:
        """Find similar table names using sophisticated matching."""
        similar_tables = []
        for table_name in schema_tables.keys():
            if self._is_similar(table, table_name):
                similar_tables.append(table_name)
        return similar_tables
    
    def _find_similar_columns(self, column: str, schema_tables: Dict) -> List[str]:
        """Find similar column names using sophisticated matching."""
        similar_columns = []
        for table_name, table_data in schema_tables.items():
            if isinstance(table_data, dict):
                columns = table_data.get('columns', {})
                for column_name in columns.keys():
                    if self._is_similar(column, column_name):
                        similar_columns.append(column_name)
        return similar_columns
    
    def _is_similar(self, str1: str, str2: str) -> bool:
        """Check if two strings are similar using fuzzy matching."""
        s1_lower = str1.lower().strip()
        s2_lower = str2.lower().strip()
        
        # Exact match
        if s1_lower == s2_lower:
            return True
        
        # Substring match (one contains the other)
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return True
        
        # Word-based similarity (checks if most words match)
        s1_words = set(s1_lower.split())
        s2_words = set(s2_lower.split())
        
        if s1_words and s2_words:
            # If one word set is mostly contained in the other
            intersection = s1_words & s2_words
            if len(intersection) > 0:
                # If significant overlap (at least 50% of smaller set)
                min_len = min(len(s1_words), len(s2_words))
                if len(intersection) >= min_len * 0.5:
                    return True
        
        # Levenshtein-like: simple edit distance for short strings
        if len(s1_lower) <= 20 and len(s2_lower) <= 20:
            if abs(len(s1_lower) - len(s2_lower)) <= 2:
                # Count character differences (simple approach)
                diff_count = sum(1 for c1, c2 in zip(s1_lower, s2_lower) if c1 != c2)
                if diff_count <= max(len(s1_lower), len(s2_lower)) * 0.3:  # 30% tolerance
                    return True
        
        return False
    
    def _enhance_filter_expression(self, filter_expr: str, user_question: str, knowledge_data: Dict) -> str:
        """Enhance filter expression by validating against schema."""
        # Validate filter expression contains valid column names
        schema = knowledge_data.get('schema', {})
        schema_tables = schema.get('tables', {})
        
        # Extract column name from filter (simple heuristic: text before operators)
        filter_lower = filter_expr.lower()
        operators = ['=', '>', '<', '>=', '<=', '!=', '<>', 'in', 'like', 'between']
        
        for op in operators:
            if op in filter_lower:
                parts = filter_lower.split(op, 1)
                if parts:
                    col_name = parts[0].strip().strip('[]"\'')
                    
                    # Check if column exists in schema
                    column_exists = False
                    for table_name, table_data in schema_tables.items():
                        if isinstance(table_data, dict):
                            columns = table_data.get('columns', {})
                            if col_name in columns:
                                column_exists = True
                                break
                    
                    if not column_exists:
                        # Try to find similar column
                        similar_cols = self._find_similar_columns(col_name, schema_tables)
                        if similar_cols:
                            return filter_expr.replace(col_name, similar_cols[0], 1)
        
        return filter_expr
    
    def _enhance_aggregation_expression(self, agg: str, user_question: str, knowledge_data: Dict) -> str:
        """Enhance aggregation expression by validating format."""
        # Validate aggregation is in proper format (e.g., "COUNT(*)", "SUM(column)", "AVG(column)")
        agg_upper = agg.upper().strip()
        
        # Standard aggregations
        valid_aggregations = ['COUNT', 'SUM', 'AVG', 'AVERAGE', 'MAX', 'MIN', 'STDDEV', 'VARIANCE']
        
        for valid_agg in valid_aggregations:
            if agg_upper.startswith(valid_agg):
                return agg  # Already in correct format
        
        # If it's just a column name, might need to wrap it
        schema = knowledge_data.get('schema', {})
        schema_tables = schema.get('tables', {})
        
        # Check if it's a column name without aggregation
        for table_name, table_data in schema_tables.items():
            if isinstance(table_data, dict):
                columns = table_data.get('columns', {})
                if agg in columns:
                    # It's a column name, but no aggregation specified - return as is
                    # Query generator will handle proper aggregation
                    return agg
        
        return agg
    
    def _calculate_table_confidence(self, tables: List[str], user_question: str, knowledge_data: Dict) -> float:
        """Calculate table confidence based on relevance to question."""
        if not tables:
            return 0.0
        
        schema = knowledge_data.get('schema', {})
        schema_tables = schema.get('tables', {})
        question_lower = user_question.lower()
        question_tokens = set(re.findall(r'\b\w+\b', question_lower))
        
        total_score = 0.0
        valid_tables = 0
        
        for table in tables:
            if table not in schema_tables:
                continue
            
            valid_tables += 1
            table_lower = table.lower()
            
            # Check if table name appears in question
            if table_lower in question_tokens:
                total_score += 1.0
            elif any(token in table_lower for token in question_tokens if len(token) > 3):
                total_score += 0.7
            
            # Check table metadata (business context, description)
            table_data = schema_tables.get(table, {})
            if isinstance(table_data, dict):
                business_context = table_data.get('business_context', '').lower()
                description = table_data.get('description', '').lower()
                
                if business_context or description:
                    context_text = (business_context + " " + description)
                    matches = sum(1 for token in question_tokens if token in context_text and len(token) > 3)
                    if matches > 0:
                        total_score += min(0.5, matches * 0.1)
        
        if valid_tables == 0:
            return 0.0
        
        avg_score = total_score / valid_tables
        return min(1.0, max(0.0, avg_score))
    
    def _calculate_column_confidence(self, columns: List[str], user_question: str, knowledge_data: Dict) -> float:
        """Calculate column confidence based on relevance to question."""
        if not columns:
            return 0.0
        
        schema = knowledge_data.get('schema', {})
        schema_tables = schema.get('tables', {})
        question_lower = user_question.lower()
        question_tokens = set(re.findall(r'\b\w+\b', question_lower))
        
        total_score = 0.0
        valid_columns = 0
        
        for col_name in columns:
            col_info = None
            found = False
            
            # Find column in schema
            for table_name, table_data in schema_tables.items():
                if isinstance(table_data, dict):
                    table_columns = table_data.get('columns', {})
                    if col_name in table_columns:
                        col_info = table_columns[col_name] if isinstance(table_columns[col_name], dict) else {}
                        found = True
                        break
            
            if not found:
                continue
            
            valid_columns += 1
            col_name_lower = col_name.lower()
            
            # Check if column name appears in question
            if col_name_lower in question_tokens:
                total_score += 1.0
            elif any(token in col_name_lower for token in question_tokens if len(token) > 3):
                total_score += 0.7
            
            # Check column description and business terms
            if col_info:
                description = col_info.get('description', '').lower()
                business_terms = col_info.get('business_terms', [])
                
                if description:
                    desc_matches = sum(1 for token in question_tokens if token in description and len(token) > 3)
                    if desc_matches > 0:
                        total_score += min(0.5, desc_matches * 0.1)
                
                if business_terms:
                    term_matches = sum(1 for term in business_terms if any(
                        token in term.lower() for token in question_tokens if len(token) > 3
                    ))
                    if term_matches > 0:
                        total_score += min(0.3, term_matches * 0.05)
        
        if valid_columns == 0:
            return 0.0
        
        avg_score = total_score / valid_columns
        return min(1.0, max(0.0, avg_score))
    
    def _calculate_filter_confidence(self, filters: List[str], user_question: str, knowledge_data: Dict) -> float:
        """Calculate filter confidence based on question alignment."""
        if not filters:
            return 0.0
        
        question_lower = user_question.lower()
        
        # Check if question contains filter-related keywords
        filter_keywords = ['where', 'filter', 'only', 'above', 'below', 'greater', 'less', 'equal', 'match', 'contain']
        has_filter_intent = any(keyword in question_lower for keyword in filter_keywords)
        
        # Check if filters contain values mentioned in question
        question_tokens = set(re.findall(r'\b\w+\b', question_lower))
        question_numbers = set(re.findall(r'\d+', user_question))
        
        matching_filters = 0
        for filter_expr in filters:
            filter_lower = filter_expr.lower()
            
            # Check for number matches
            filter_numbers = set(re.findall(r'\d+', filter_expr))
            if filter_numbers and question_numbers:
                if filter_numbers & question_numbers:
                    matching_filters += 1
                    continue
            
            # Check for token matches
            filter_tokens = set(re.findall(r'\b\w+\b', filter_lower))
            if filter_tokens & question_tokens:
                matching_filters += 1
        
        base_confidence = 0.5 if has_filter_intent else 0.3
        if matching_filters > 0:
            base_confidence += min(0.4, matching_filters / len(filters) * 0.4)
        
        return min(1.0, base_confidence)
    
    def _calculate_aggregation_confidence(self, aggregations: List[str], user_question: str, knowledge_data: Dict) -> float:
        """Calculate aggregation confidence based on question alignment."""
        if not aggregations:
            return 0.0
        
        question_lower = user_question.lower()
        
        # Check for aggregation keywords in question
        agg_keywords = ['count', 'sum', 'total', 'average', 'avg', 'maximum', 'max', 'minimum', 'min', 'mean']
        has_agg_intent = any(keyword in question_lower for keyword in agg_keywords)
        
        # Check if aggregations match question intent
        matching_aggs = 0
        for agg in aggregations:
            agg_lower = agg.lower()
            for keyword in agg_keywords:
                if keyword in agg_lower:
                    matching_aggs += 1
                    break
        
        base_confidence = 0.7 if has_agg_intent else 0.4
        if matching_aggs > 0:
            base_confidence += min(0.2, matching_aggs / len(aggregations) * 0.2)
        
        return min(1.0, base_confidence)
    
    def _generate_agent_thoughts(self, question: str, intent: Dict, schema_data: Dict, confidence_scores: Dict) -> str:
        """Generate the agent's actual internal thoughts using LLM reasoning."""
        # Use the LLM to generate its own internal reasoning
        prompt = f"""
You are an AI agent that analyzes user questions and selects relevant database tables and columns. 
Show your internal thought process as you make decisions.

User Question: "{question}"

Available Schema:
Tables: {list(schema_data.get('tables', {}).keys())}
Schema Details: {schema_data}

Your Task: Show your internal reasoning process as you decide which tables and columns to select.

Think step by step:
1. What do you notice about the user's question?
2. What tables seem relevant and why?
3. What columns do you need and why?
4. What filters should you apply and why?
5. How confident are you in each decision?

Show your actual thought process, not just the final result.
"""

        try:
            # Get the LLM to generate its own internal thoughts (use messages format for consistency)
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error generating internal thoughts: {e}"
    
    def _extract_key_terms(self, question: str) -> List[str]:
        """Extract key terms from the question."""
        import re
        # Extract meaningful terms (not common words)
        words = re.findall(r'\b\w+\b', question.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'have', 'has', 'had', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]
        return key_terms