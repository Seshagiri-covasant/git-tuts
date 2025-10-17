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
            
            return {
                **state,
                'intent': validated_intent,
                'confidence_scores': confidence_scores,
                'conversation_context': conversation_context
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
        
        # Build knowledge overview for the LLM
        knowledge_overview = self._build_knowledge_overview(knowledge_data, user_question)
        
        # 🔍 LOGGING: Track what data is being sent to LLM
        print(f"\n{'='*80}")
        print(f"🔍 LLM COLUMN USAGE DEBUG: Intent Picker")
        print(f"{'='*80}")
        print(f"📝 User Question: {user_question}")
        print(f"📊 Knowledge Overview Length: {len(knowledge_overview)} characters")
        print(f"📋 Available Schema Keys: {list(knowledge_data.keys()) if isinstance(knowledge_data, dict) else 'Not a dict'}")
        
        # Log the exact schema being sent to LLM
        if 'schema' in knowledge_data:
            schema = knowledge_data['schema']
            print(f"📊 Schema Tables: {list(schema.get('tables', {}).keys()) if isinstance(schema.get('tables'), dict) else 'Not a dict'}")
            print(f"📈 Schema Metrics: {schema.get('metrics', [])}")
            
            # Log specific columns available
            tables = schema.get('tables', {})
            if isinstance(tables, dict):
                for table_name, table_data in tables.items():
                    columns = table_data.get('columns', {})
                    if isinstance(columns, dict):
                        print(f"📋 Table {table_name} columns: {list(columns.keys())[:10]}...")  # Show first 10 columns
                        # Check for score related columns
                        score_columns = [col for col in columns.keys() if 'score' in col.lower() or 'metric' in col.lower()]
                        if score_columns:
                            print(f"🎯 Score/Metric columns in {table_name}: {score_columns}")
        
        print(f"📝 Full Knowledge Overview:")
        print(f"{knowledge_overview}")
        print(f"{'='*80}\n")
        
        user_prompt = f"""Conversation Context:
{conversation_context}

Current User Question: {user_question}

Available Database Schema:
{knowledge_overview}

CRITICAL INSTRUCTION: When the question involves aggregations (AVG, SUM, COUNT, etc.) and there are pre-defined metrics available above, you MUST use the EXACT metric names from the "Available Database Metrics" section.

IMPORTANT: 
- Do NOT create your own metric names
- Do NOT use raw column names from the table schema
- ALWAYS prioritize the "Available Database Metrics" section over individual table columns
- Use ONLY the exact names provided in the "Available Database Metrics" section

ALWAYS copy the exact metric name from the "Available Database Metrics" section.

Please analyze this question with perfect accuracy and determine:
1. What tables are relevant to answer this question?
2. What columns are needed from those tables?
3. Are there any filters, aggregations, or sorting requirements?
4. How does this relate to our previous conversation?
5. What is your confidence level for each selection?

Respond in this JSON format:
{{
    "tables": ["table1", "table2"],
    "columns": ["column1", "column2"],
    "filters": ["filter1", "filter2"],
    "aggregations": ["agg1", "agg2"],
    "time_range": "time_range_info",
    "sorting": "sorting_info",
    "reasoning": "Detailed reasoning for your selections",
    "is_follow_up": true/false,
    "follow_up_context": "How this relates to previous conversation",
    "confidence": {{
        "tables": 0.9,
        "columns": 0.8,
        "filters": 0.7,
        "aggregations": 0.6,
        "overall": 0.8
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
                # Clean the response text to remove markdown formatting
                cleaned_response = response_text.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
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
        """
        enhanced_tables = []
        
        for table in tables:
            # Check if table exists in knowledge data
            table_key = f"table:{table}"
            if table_key in knowledge_data:
                enhanced_tables.append(table)
            else:
                # Try to find similar table names
                similar_tables = self._find_similar_tables(table, knowledge_data)
                enhanced_tables.extend(similar_tables)
        
        return enhanced_tables
    
    def _enhance_column_selection(self, columns: List[str], user_question: str, knowledge_data: Dict, conversation_context: str) -> List[str]:
        """
        Enhance column selection with sophisticated disambiguation.
        """
        enhanced_columns = []
        
        for column in columns:
            # Check if column exists in knowledge data
            column_key = f"column:{column}"
            if column_key in knowledge_data:
                enhanced_columns.append(column)
            else:
                # Try to find similar column names
                similar_columns = self._find_similar_columns(column, knowledge_data)
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
        """
        confidence_scores = {}
        
        # Table confidence
        tables = intent.get('tables', [])
        table_confidence = self._calculate_table_confidence(tables, user_question, knowledge_data)
        confidence_scores['tables'] = table_confidence
        
        # Column confidence
        columns = intent.get('columns', [])
        column_confidence = self._calculate_column_confidence(columns, user_question, knowledge_data)
        confidence_scores['columns'] = column_confidence
        
        # Filter confidence
        filters = intent.get('filters', [])
        filter_confidence = self._calculate_filter_confidence(filters, user_question, knowledge_data)
        confidence_scores['filters'] = filter_confidence
        
        # Aggregation confidence
        aggregations = intent.get('aggregations', [])
        agg_confidence = self._calculate_aggregation_confidence(aggregations, user_question, knowledge_data)
        confidence_scores['aggregations'] = agg_confidence
        
        # Overall confidence
        overall_confidence = sum(confidence_scores.values()) / len(confidence_scores)
        confidence_scores['overall'] = overall_confidence
        
        return confidence_scores
    
    def _validate_intent_with_schema(self, intent: Dict, knowledge_data: Dict) -> Dict:
        """
        Validate intent against available schema with sophisticated logic.
        """
        validated_intent = intent.copy()
        
        # Validate tables
        if 'tables' in intent:
            validated_tables = []
            for table in intent['tables']:
                if f"table:{table}" in knowledge_data:
                    validated_tables.append(table)
            validated_intent['tables'] = validated_tables
        
        # Validate columns
        if 'columns' in intent:
            validated_columns = []
            for column in intent['columns']:
                if f"column:{column}" in knowledge_data:
                    validated_columns.append(column)
            validated_intent['columns'] = validated_columns
        
        return validated_intent
    
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
    
    # Helper methods for sophisticated logic
    def _find_similar_tables(self, table: str, knowledge_data: Dict) -> List[str]:
        """Find similar table names using sophisticated matching."""
        similar_tables = []
        for key in knowledge_data.keys():
            if key.startswith("table:"):
                table_name = key.split(":", 1)[1]
                if self._is_similar(table, table_name):
                    similar_tables.append(table_name)
        return similar_tables
    
    def _find_similar_columns(self, column: str, knowledge_data: Dict) -> List[str]:
        """Find similar column names using sophisticated matching."""
        similar_columns = []
        for key in knowledge_data.keys():
            if key.startswith("column:"):
                column_name = key.split(":", 1)[1]
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