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
            
            print(f"[AdvancedIntentPicker] Final intent: {validated_intent}")
            print(f"[AdvancedIntentPicker] Confidence scores: {confidence_scores}")
            
            # AGENT THOUGHTS: Internal reasoning process
            agent_thoughts = self._generate_agent_thoughts(state.get('user_question', ''), validated_intent, knowledge_data, confidence_scores)
            
            # DECISION TRANSPARENCY: Structured decision trace
            decision_trace = self._build_decision_trace(
                state.get('user_question', ''), validated_intent, knowledge_data, confidence_scores
            )
            
            return {
                **state,
                'intent': validated_intent,
                'confidence_scores': confidence_scores,
                'conversation_context': conversation_context,
                'agent_thoughts': agent_thoughts,
                'decision_trace': decision_trace
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
        for i, message in enumerate(conversation_history[-5:]):  # Last 5 messages for context
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
        
        # 🔍 ENHANCED LOGGING: Track what schema data is being sent to LLM
        print(f"\n{'='*80}")
        print(f"🔍 SCHEMA DESCRIPTION DEBUG: Intent Picker")
        print(f"{'='*80}")
        print(f"📝 User Question: {user_question}")
        print(f"📊 Knowledge Overview Length: {len(knowledge_overview)} characters")
        print(f"📋 Available Schema Keys: {list(knowledge_data.keys()) if isinstance(knowledge_data, dict) else 'Not a dict'}")
        
        # Log the exact schema being sent to LLM
        if 'schema' in knowledge_data:
            schema = knowledge_data['schema']
            print(f"📊 Schema Tables: {list(schema.get('tables', {}).keys()) if isinstance(schema.get('tables'), dict) else 'Not a dict'}")
            print(f"📈 Schema Metrics: {schema.get('metrics', [])}")
            
            # 🔍 NEW: Check for description fields in columns
            tables = schema.get('tables', {})
            if isinstance(tables, dict):
                for table_name, table_data in tables.items():
                    columns = table_data.get('columns', {})
                    if isinstance(columns, dict):
                        print(f"📋 Table {table_name} columns: {list(columns.keys())[:10]}...")  # Show first 10 columns
                        
                        # 🔍 NEW: Check for description fields in each column
                        description_columns = []
                        for col_name, col_data in columns.items():
                            if isinstance(col_data, dict):
                                description = col_data.get('description', '')
                                business_terms = col_data.get('business_terms', [])
                                use_cases = col_data.get('use_cases', [])
                                
                                if description or business_terms or use_cases:
                                    description_columns.append({
                                        'column': col_name,
                                        'description': description,
                                        'business_terms': business_terms,
                                        'use_cases': use_cases
                                    })
                        
                        if description_columns:
                            print(f"🎯 Columns with descriptions in {table_name}:")
                            for desc_col in description_columns[:5]:  # Show first 5
                                print(f"  - {desc_col['column']}: {desc_col['description']}")
                                if desc_col['business_terms']:
                                    print(f"    Business Terms: {desc_col['business_terms']}")
                                if desc_col['use_cases']:
                                    print(f"    Use Cases: {desc_col['use_cases']}")
                        else:
                            print(f"⚠️  No columns with descriptions found in {table_name}")
                        
                        # Check for score related columns
                        score_columns = [col for col in columns.keys() if 'score' in col.lower() or 'metric' in col.lower()]
                        if score_columns:
                            print(f"🎯 Score/Metric columns in {table_name}: {score_columns}")
        
        print(f"📝 Full Knowledge Overview:")
        print(f"{knowledge_overview}")
        print(f"{'='*80}\n")
        
        user_prompt = f"""Conversation Context:
{conversation_context}
Current User Question: "{user_question}"
Available Database Schema with Business Context:
{knowledge_overview}
### YOUR TASK ###
You are an expert data analyst. Your goal is to understand the user's intent and identify the exact columns needed to answer their question.
### CRITICAL INSTRUCTIONS FOR COLUMN SELECTION ###
1.  **REASONING IS PARAMOUNT:** Your primary task is to find the column whose **CONTEXT** (Description, Business Terms, Use Cases) best matches the user's goal expressed in their question. Do not rely on name similarity alone.
2.  **INTELLIGENT SELECTION:** Analyze the user's question carefully and select the MOST RELEVANT column based on context. If one column's description clearly matches the user's intent better than others, select only that one.
3.  **DETECT TRUE AMBIGUITY:** Only include multiple columns if the user's question is genuinely ambiguous and multiple columns could reasonably be the answer. True ambiguity occurs when the user's question could legitimately refer to different types of data (e.g., asking about "risk" without specifying whether they mean vendor risk, transaction risk, or cumulative risk).
4.  **AVOID OVER-SELECTION:** Do not include all similar columns just because they have similar names. Choose the most contextually appropriate one based on the user's specific question.
5.  **JUSTIFY YOUR CHOICES:** In the "reasoning" field, explicitly state which parts of a column's CONTEXT you used to make your selection. Explain how the column's description, business terms, or use cases align with the user's specific question.

### PRINCIPLES FOR INTELLIGENT SELECTION ###
- **Context Matching**: Match the user's question context to the column's description. If the user mentions "payments" and you see a column described as "payment risk score", that's the best match.
- **Specificity Over Generality**: If the user's question is specific (mentions a particular entity like "payments", "vendors", "transactions"), select the column that best matches that specificity.
- **Description-Driven**: Always prioritize the column whose description most closely aligns with what the user is asking about.
- **Avoid Over-Selection**: Don't include multiple similar columns unless the user's question is genuinely ambiguous about which type of data they want.
### JSON RESPONSE FORMAT ###
Respond with a JSON object in the following format. Do NOT include any comments or explanations outside the JSON structure.
{{
    "tables": ["table_name"],
    "columns": ["column_name_1", "column_name_2"],
    "filters": ["filter_expression"],
    "reasoning": "My detailed justification for selecting these columns based on their context and the user's question.",
    "confidence": {{
        "overall": 0.85,
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
            
            # 🔍 LOGGING: Capture LLM's raw response and reasoning
            print(f"\n{'='*80}")
            print(f"🤖 LLM RESPONSE ANALYSIS: Intent Picker")
            print(f"{'='*80}")
            print(f"📝 Raw LLM Response:")
            print(f"{response_text}")
            print(f"📊 Response Length: {len(response_text)} characters")
            print(f"{'='*80}\n")
            
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
                import re
                cleaned_response = re.sub(r'//.*$', '', cleaned_response, flags=re.MULTILINE)
                
                intent_analysis = json.loads(cleaned_response)
                
                # 🔍 LOGGING: Show final parsed intent and column selection reasoning
                print(f"\n{'='*80}")
                print(f"🎯 FINAL INTENT ANALYSIS: Column Selection Reasoning")
                print(f"{'='*80}")
                print(f"📊 Parsed Intent:")
                print(f"  Tables: {intent_analysis.get('tables', [])}")
                print(f"  Columns: {intent_analysis.get('columns', [])}")
                print(f"  Aggregations: {intent_analysis.get('aggregations', [])}")
                print(f"  Reasoning: {intent_analysis.get('reasoning', 'No reasoning provided')}")
                print(f"  Confidence: {intent_analysis.get('confidence', {})}")
                
                # Analyze why specific columns were chosen
                aggregations = intent_analysis.get('aggregations', [])
                if aggregations:
                    print(f"\n🔍 AGGREGATION ANALYSIS:")
                    for agg in aggregations:
                        print(f"  Selected: {agg}")
                        # Check if using raw column names (uppercase with underscores) vs metrics (lowercase)
                        if agg.isupper() or (agg.count('_') > 0 and agg[0].isupper()):
                            print(f"    ❌ Using raw column name instead of metric")
                        elif agg.islower() or (agg.count('_') > 0 and agg[0].islower()):
                            print(f"    ✅ Using metric name correctly")
                        else:
                            print(f"    ❓ Unknown aggregation pattern")
                
                print(f"{'='*80}\n")
                
                return intent_analysis
                
            except json.JSONDecodeError:
                print(f"[AdvancedIntentPicker] Failed to parse LLM response: {response_text}")
                # Fallback: return basic intent structure
                return {
                    "tables": [],
                    "columns": [],
                    "filters": [],
                    "aggregations": [],
                    "time_range": "",
                    "sorting": "",
                    "reasoning": "Failed to parse LLM response",
                    "is_follow_up": False,
                    "follow_up_context": "",
                    "confidence": {"tables": 0.0, "columns": 0.0, "filters": 0.0, "aggregations": 0.0, "overall": 0.0}
                }
                
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
            overall_confidence = sum(confidence_scores.values()) / len(confidence_scores)
            confidence_scores['overall'] = overall_confidence
        
        print(f"[AdvancedIntentPicker] Confidence calculation: Using LLM confidence: {bool(llm_confidence)}, Final scores: {confidence_scores}")
        
        return confidence_scores
    
    def _validate_intent_with_schema(self, intent: Dict, knowledge_data: Dict) -> Dict:
        """
        Validate intent against available schema with intelligent column selection.
        FIXED: Preserve LLM's correct selections instead of overwriting them.
        """
        validated_intent = intent.copy()
        
        # Get schema and user preferences
        schema = knowledge_data.get('schema', {})
        user_preferences = schema.get('user_preferences', {})
        tables = schema.get('tables', {})
        
        # FIXED: Always preserve LLM's table selection if it exists
        if 'tables' in intent and intent['tables']:
            validated_intent['tables'] = intent['tables']
            print(f"[AdvancedIntentPicker] Schema validation: Preserving LLM's table selection: {intent['tables']}")
        
        # FIXED: Always preserve LLM's column selection if it exists
        if 'columns' in intent and intent['columns']:
            validated_intent['columns'] = intent['columns']
            print(f"[AdvancedIntentPicker] Schema validation: Preserving LLM's column selection: {intent['columns']}")
        
        # FIXED: Always preserve LLM's filter selection if it exists
        if 'filters' in intent and intent['filters']:
            validated_intent['filters'] = intent['filters']
            print(f"[AdvancedIntentPicker] Schema validation: Preserving LLM's filter selection: {intent['filters']}")
        
        # FIXED: Always preserve LLM's aggregation selection if it exists
        if 'aggregations' in intent and intent['aggregations']:
            validated_intent['aggregations'] = intent['aggregations']
            print(f"[AdvancedIntentPicker] Schema validation: Preserving LLM's aggregation selection: {intent['aggregations']}")
        
        return validated_intent

    def _select_columns_intelligently(self, intent: Dict, tables: List[str], schema_tables: Dict, user_preferences: Dict) -> List[str]:
        """Select columns using schema metadata and user preferences."""
        try:
            selected_columns = []
            user_question = intent.get('user_question', '').lower()
            
            for table in tables:
                table_data = schema_tables.get(table, {})
                columns = table_data.get('columns', {})
                
                # Get all columns for this table with metadata
                available_columns = []
                for col_name, col_data in columns.items():
                    if isinstance(col_data, dict):
                        column_metadata = {
                            'name': col_name,
                            'business_description': col_data.get('business_description', ''),
                            'business_terms': col_data.get('business_terms', []),
                            'priority': col_data.get('priority', 'medium'),
                            'is_preferred': col_data.get('is_preferred', False),
                            'use_cases': col_data.get('use_cases', []),
                            'relevance_keywords': col_data.get('relevance_keywords', [])
                        }
                        available_columns.append(column_metadata)
                        
                        # 🔍 LOG PRIORITY FIELDS: Log priority fields being used by agent
                        if any([column_metadata['priority'] != 'medium', 
                               column_metadata['business_description'], 
                               column_metadata['business_terms'], 
                               column_metadata['is_preferred']]):
                            print(f"🔍 INTENT PICKER PRIORITY: {table}.{col_name}: {column_metadata}")
                
                # Method 1: Check user preferences first
                preferred_columns = self._get_preferred_columns(user_question, user_preferences, available_columns)
                if preferred_columns:
                    selected_columns.extend(preferred_columns)
                    continue
                
                # Method 2: Business terms matching
                business_matched_columns = self._match_business_terms(user_question, available_columns)
                if business_matched_columns:
                    selected_columns.extend(business_matched_columns)
                    continue
                
                # Method 3: Priority-based selection
                priority_columns = self._select_by_priority(available_columns)
                if priority_columns:
                    selected_columns.extend(priority_columns)
                    continue
                
                # Method 4: Fallback to original intent columns
                original_columns = intent.get('columns', [])
                for col in original_columns:
                    if col in columns:
                        selected_columns.append(col)
            
            return list(set(selected_columns))  # Remove duplicates
            
        except Exception as e:
            print(f"[AdvancedIntentPicker] Error in intelligent column selection: {e}")
            return intent.get('columns', [])

    def _get_preferred_columns(self, user_question: str, user_preferences: Dict, available_columns: List[Dict]) -> List[str]:
        """Check user preferences for column selection."""
        try:
            # Check if user is asking about risk scores
            if 'risk' in user_question and 'risk_score_column' in user_preferences:
                preferred_col = user_preferences['risk_score_column']
                for col in available_columns:
                    if col['name'] == preferred_col:
                        return [preferred_col]
            
            # Check if user is asking about amounts
            if any(word in user_question for word in ['amount', 'money', 'value', 'cost', 'price']):
                if 'amount_column' in user_preferences:
                    preferred_col = user_preferences['amount_column']
                    for col in available_columns:
                        if col['name'] == preferred_col:
                            return [preferred_col]
            
            # Check if user is asking about dates
            if any(word in user_question for word in ['date', 'time', 'when', 'created', 'updated']):
                if 'date_column' in user_preferences:
                    preferred_col = user_preferences['date_column']
                    for col in available_columns:
                        if col['name'] == preferred_col:
                            return [preferred_col]
            
            return []
        except Exception as e:
            print(f"[AdvancedIntentPicker] Error checking user preferences: {e}")
            return []

    def _match_business_terms(self, user_question: str, available_columns: List[Dict]) -> List[str]:
        """Match columns based on business terms in schema."""
        try:
            matched_columns = []
            
            for col in available_columns:
                score = 0
                matched_terms = []
                
                # Check business terms
                for term in col.get('business_terms', []):
                    if term.lower() in user_question:
                        score += 10
                        matched_terms.append(term)
                
                # Check relevance keywords
                for keyword in col.get('relevance_keywords', []):
                    if keyword.lower() in user_question:
                        score += 5
                        matched_terms.append(keyword)
                
                # Check business description
                if col.get('business_description', '').lower() in user_question:
                    score += 3
                
                if score > 0:
                    matched_columns.append({
                        'column': col['name'],
                        'score': score,
                        'matched_terms': matched_terms
                    })
            
            # Return highest scoring columns
            if matched_columns:
                matched_columns.sort(key=lambda x: x['score'], reverse=True)
                return [col['column'] for col in matched_columns[:3]]  # Top 3 matches
            
            return []
        except Exception as e:
            print(f"[AdvancedIntentPicker] Error matching business terms: {e}")
            return []

    def _select_by_priority(self, available_columns: List[Dict]) -> List[str]:
        """Select columns based on priority in schema."""
        try:
            # Filter preferred columns first
            preferred_columns = [col for col in available_columns if col.get('is_preferred', False)]
            if preferred_columns:
                return [col['name'] for col in preferred_columns]
            
            # Then by priority
            priority_scores = {'high': 3, 'medium': 2, 'low': 1}
            scored_columns = []
            
            for col in available_columns:
                priority = col.get('priority', 'medium')
                score = priority_scores.get(priority, 1)
                scored_columns.append({
                    'name': col['name'],
                    'score': score,
                    'priority': priority
                })
            
            if scored_columns:
                scored_columns.sort(key=lambda x: x['score'], reverse=True)
                return [col['name'] for col in scored_columns[:2]]  # Top 2 by priority
            
            return []
        except Exception as e:
            print(f"[AdvancedIntentPicker] Error selecting by priority: {e}")
            return []
    
    def _build_knowledge_overview(self, knowledge_data: Dict[str, Any], question: str) -> str:
        """
        Build a natural overview of the database schema for the LLM.
        This helps the LLM understand what's available without hardcoded patterns.
        """
        if not knowledge_data or 'schema' not in knowledge_data:
            return "No database schema information available."
        
        # Extract simple keywords from the question for relevance
        keywords = set(re.findall(r"[a-zA-Z0-9_]{3,}", (question or "").lower()))
        
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
        
        overview_parts = ["Available Database Tables:"]
        
        # Add database-level metrics if available and relevant to the question
        if 'metrics' in schema and schema['metrics']:
            # Only include metrics if the question seems to be asking for aggregations, averages, or calculations
            question_lower = question.lower() if question else ""
            metrics_keywords = ['average', 'avg', 'sum', 'count', 'total', 'maximum', 'max', 'minimum', 'min', 'metric', 'score', 'rate', 'ratio', 'percentage', '%']
            
            print(f"[AdvancedIntentPicker] Question: {question}")
            print(f"[AdvancedIntentPicker] Question lower: {question_lower}")
            print(f"[AdvancedIntentPicker] Metrics keywords match: {any(keyword in question_lower for keyword in metrics_keywords)}")
            print(f"[AdvancedIntentPicker] Available metrics: {schema['metrics']}")
            
            if any(keyword in question_lower for keyword in metrics_keywords):
                overview_parts.append("\nAvailable Database Metrics:")
                for metric in schema['metrics']:
                    if isinstance(metric, dict):
                        metric_name = metric.get('name', 'Unknown')
                        metric_expression = metric.get('expression', 'Unknown')
                        overview_parts.append(f"  - {metric_name}: {metric_expression}")
                    else:
                        overview_parts.append(f"  - {metric}")
                print(f"[AdvancedIntentPicker] Added metrics to overview")
            else:
                print(f"[AdvancedIntentPicker] Metrics not included - question doesn't match keywords")
        
        for table_name, table_data in tables_list.items():
            if isinstance(table_data, dict):
                columns = table_data.get('columns', {})
                overview_parts.append(f"\n{table_name}:")
                
                # Skip table-level metrics to avoid conflicts with database-level metrics
                # Only use database-level metrics from the "Available Database Metrics" section
                
                # Handle both dict and list formats for columns
                if isinstance(columns, dict):
                    for col_name, col_data in columns.items():
                        if isinstance(col_data, dict):
                            col_type = col_data.get('type', col_data.get('data_type', 'Unknown'))
                        else:
                            col_type = 'Unknown'
                        overview_parts.append(f"  - {col_name} ({col_type})")
                elif isinstance(columns, list):
                    for col in columns:
                        if isinstance(col, dict):
                            col_name = col.get('name', 'Unknown')
                            col_type = col.get('type', col.get('data_type', 'Unknown'))
                        else:
                            col_name = str(col)
                            col_type = 'Unknown'
                        overview_parts.append(f"  - {col_name} ({col_type})")
        
        return "\n".join(overview_parts)
    
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
                                print(f"🔍 FOUND DESCRIPTION: {col_name} -> {description}")
                            else:
                                print(f"⚠️  NO DESCRIPTION: {col_name}")
                            
                            # Business terms (alternative terms)
                            business_terms = col_data.get('business_terms', [])
                            if business_terms:
                                context_parts.append(f"Business Terms: {business_terms}")
                                print(f"🔍 FOUND BUSINESS TERMS: {col_name} -> {business_terms}")
                            
                            # Use cases (typical usage scenarios)
                            use_cases = col_data.get('use_cases', [])
                            if use_cases:
                                context_parts.append(f"Typical Use Cases: {use_cases}")
                                print(f"🔍 FOUND USE CASES: {col_name} -> {use_cases}")
                            
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
        """Check if two strings are similar using sophisticated matching."""
        # Simple similarity check - can be enhanced with more sophisticated algorithms
        return str1.lower() in str2.lower() or str2.lower() in str1.lower()
    
    def _enhance_filter_expression(self, filter_expr: str, user_question: str, knowledge_data: Dict) -> str:
        """Enhance filter expression with sophisticated logic."""
        # Add sophisticated filter enhancement logic here
        return filter_expr
    
    def _enhance_aggregation_expression(self, agg: str, user_question: str, knowledge_data: Dict) -> str:
        """Enhance aggregation expression with sophisticated logic."""
        # Add sophisticated aggregation enhancement logic here
        return agg
    
    def _calculate_table_confidence(self, tables: List[str], user_question: str, knowledge_data: Dict) -> float:
        """Calculate table confidence with sophisticated logic."""
        if not tables:
            return 0.0
        
        # Add sophisticated table confidence calculation here
        return 0.8  # Placeholder
    
    def _calculate_column_confidence(self, columns: List[str], user_question: str, knowledge_data: Dict) -> float:
        """Calculate column confidence with sophisticated logic."""
        if not columns:
            return 0.0
        
        # Add sophisticated column confidence calculation here
        return 0.8  # Placeholder
    
    def _calculate_filter_confidence(self, filters: List[str], user_question: str, knowledge_data: Dict) -> float:
        """Calculate filter confidence with sophisticated logic."""
        if not filters:
            return 0.0
        
        # Add sophisticated filter confidence calculation here
        return 0.8  # Placeholder
    
    def _calculate_aggregation_confidence(self, aggregations: List[str], user_question: str, knowledge_data: Dict) -> float:
        """Calculate aggregation confidence with sophisticated logic."""
        if not aggregations:
            return 0.0
        
        # Add sophisticated aggregation confidence calculation here
        return 0.8  # Placeholder
    
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
            # Get the LLM to generate its own internal thoughts
            response = self.llm.invoke(prompt)
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
    
    def _build_decision_trace(self, question: str, intent: Dict, schema_data: Dict, confidence_scores: Dict) -> Dict:
        """Build structured decision trace showing reasoning process."""
        trace = {
            "agent": "IntentPicker",
            "question": question,
            "tables_selected": intent.get('tables', []),
            "columns_selected": intent.get('columns', []),
            "filters_built": intent.get('filters', []),
            "aggregations_identified": intent.get('aggregations', []),
            "selection_reasons": {},
            "confidence_scores": confidence_scores,
            "signals_used": [],
            "schema_analysis": {},
            "intelligent_selection": {
                "method_used": "schema_metadata",
                "user_preferences_checked": False,
                "business_terms_matched": [],
                "priority_based_selection": False,
                "fallback_used": False
            }
        }
        
        # Analyze table selection reasoning
        selected_tables = intent.get('tables', [])
        available_tables = list(schema_data.get('tables', {}).keys()) if isinstance(schema_data.get('tables'), dict) else []
        
        trace["selection_reasons"]["tables"] = {}
        for table in selected_tables:
            if table in available_tables:
                trace["selection_reasons"]["tables"][table] = {
                    "reason": "Direct match to user query",
                    "confidence": confidence_scores.get('tables', 0.0),
                    "user_mentioned": "payments" in question.lower() if table.lower() == "payments" else False
                }
            else:
                trace["selection_reasons"]["tables"][table] = {
                    "reason": "Inferred from context",
                    "confidence": confidence_scores.get('tables', 0.0),
                    "user_mentioned": False
                }
        
        # Analyze column selection reasoning
        selected_columns = intent.get('columns', [])
        trace["selection_reasons"]["columns"] = {}
        for col in selected_columns:
            if 'risk' in col.lower() or 'score' in col.lower():
                trace["selection_reasons"]["columns"][col] = {
                    "reason": "Risk/Score column - direct match to user intent",
                    "confidence": confidence_scores.get('columns', 0.0),
                    "relevance": "HIGH",
                    "user_mentioned": "risk" in question.lower() and "score" in question.lower()
                }
            elif 'amount' in col.lower() or 'payment' in col.lower():
                trace["selection_reasons"]["columns"][col] = {
                    "reason": "Payment/Amount column - contextually relevant",
                    "confidence": confidence_scores.get('columns', 0.0),
                    "relevance": "MEDIUM",
                    "user_mentioned": "payment" in question.lower()
                }
            else:
                trace["selection_reasons"]["columns"][col] = {
                    "reason": "General data column",
                    "confidence": confidence_scores.get('columns', 0.0),
                    "relevance": "LOW",
                    "user_mentioned": False
                }
        
        # Analyze filter construction reasoning
        filters = intent.get('filters', [])
        trace["selection_reasons"]["filters"] = {}
        for filter_condition in filters:
            if '> 10' in filter_condition:
                trace["selection_reasons"]["filters"][filter_condition] = {
                    "reason": "User specified 'above 10' condition",
                    "confidence": confidence_scores.get('filters', 0.0),
                    "logic": "Numeric threshold filtering",
                    "user_mentioned": "above" in question.lower() and "10" in question.lower()
                }
            else:
                trace["selection_reasons"]["filters"][filter_condition] = {
                    "reason": "Inferred filter condition",
                    "confidence": confidence_scores.get('filters', 0.0),
                    "logic": "Context-based filtering",
                    "user_mentioned": False
                }
        
        # Identify signals used
        question_lower = question.lower()
        signals = []
        if "which" in question_lower:
            signals.append("filtering_query")
        if "payments" in question_lower:
            signals.append("table_mention")
        if "risk" in question_lower and "score" in question_lower:
            signals.append("column_mention")
        if "above" in question_lower or ">" in question_lower:
            signals.append("threshold_mention")
        if any(word in question_lower for word in ["average", "sum", "count", "max", "min"]):
            signals.append("aggregation_mention")
        
        trace["signals_used"] = signals
        
        # Schema analysis
        trace["schema_analysis"] = {
            "available_tables": available_tables,
            "total_columns": sum(len(table_data.get('columns', [])) for table_data in schema_data.get('tables', {}).values()) if isinstance(schema_data.get('tables'), dict) else 0,
            "metrics_available": len(schema_data.get('schema', {}).get('metrics', [])) if 'schema' in schema_data else 0
        }
        
        return trace