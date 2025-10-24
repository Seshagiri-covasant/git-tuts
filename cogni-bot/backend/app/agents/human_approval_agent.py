#!/usr/bin/env python3
"""
Human Approval Agent for Intent Validation
- Handles human-in-the-loop approval after intent analysis
- Detects similar columns and asks for user confirmation
- Provides professional clarification questions
- Uses LangGraph interrupts for human interaction
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseLanguageModel


class HumanApprovalAgent:
    """
    Human-in-the-loop agent that validates intent and asks for user approval.
    Detects similar columns and provides professional clarification questions.
    """
    
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
        self._current_knowledge_data = {}
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method that handles human approval and clarification.
        Uses LangGraph interrupts to pause workflow for human input.
        """
        try:
            user_question = state.get('user_question', '')
            intent = state.get('intent', {})
            knowledge_data = state.get('knowledge_data', {})
            conversation_history = state.get('conversation_history', [])
            
            # Store knowledge_data for use in other methods
            self._current_knowledge_data = knowledge_data
            
            print(f"[HumanApprovalAgent] Processing intent for approval")
            print(f"[HumanApprovalAgent] User question: {user_question}")
            print(f"[HumanApprovalAgent] Intent: {intent}")
            print(f"[HumanApprovalAgent] Intent tables: {intent.get('tables', [])}")
            print(f"[HumanApprovalAgent] Intent columns: {intent.get('columns', [])}")
            print(f"[HumanApprovalAgent] Intent filters: {intent.get('filters', [])}")
            
            # Generate unique conversation thread ID for linking follow-up questions
            import uuid
            conversation_thread = state.get('conversation_thread', str(uuid.uuid4()))
            
            print(f"[HumanApprovalAgent] Conversation thread: {conversation_thread}")
            print(f"[HumanApprovalAgent] Original question: {user_question}")
            
            # Log schema information being used
            if 'schema' in knowledge_data:
                schema = knowledge_data['schema']
                print(f"[HumanApprovalAgent] Schema Tables: {list(schema.get('tables', {}).keys()) if isinstance(schema.get('tables'), dict) else 'Not a dict'}")
                print(f"[HumanApprovalAgent] Schema Metrics: {schema.get('metrics', [])}")
                print(f"[HumanApprovalAgent] Schema AI Preferences: {schema.get('ai_preferences', [])}")
                print(f"[HumanApprovalAgent] Schema Aggregation Patterns: {schema.get('aggregation_patterns', [])}")
            else:
                print(f"[HumanApprovalAgent] No schema information available in knowledge_data")
                print(f"[HumanApprovalAgent] Knowledge data keys: {list(knowledge_data.keys()) if knowledge_data else 'None'}")
            
            # Step 1: Analyze intent for potential ambiguities
            ambiguity_analysis = self._analyze_intent_ambiguities(intent, knowledge_data, user_question)
            
            # Log if AI preferences are being used
            if 'schema' in knowledge_data:
                schema = knowledge_data['schema']
                ai_preferences = schema.get('ai_preferences', [])
                if ai_preferences:
                    print(f"[HumanApprovalAgent] Using {len(ai_preferences)} AI preferences from updated schema")
                    for pref in ai_preferences:
                        print(f"[HumanApprovalAgent] AI Preference: {pref.get('name', 'Unknown')} = {pref.get('value', 'No value')}")
                else:
                    print(f"[HumanApprovalAgent] No AI preferences found in schema")
                
                # Log if metrics are being used
                metrics = schema.get('metrics', [])
                if metrics:
                    print(f"[HumanApprovalAgent] Using {len(metrics)} business metrics from updated schema")
                    for metric in metrics:
                        print(f"[HumanApprovalAgent] Metric: {metric.get('name', 'Unknown')} = {metric.get('expression', 'No expression')}")
                else:
                    print(f"[HumanApprovalAgent] No business metrics found in schema")
            
            # Step 2: Detect similar columns that might cause confusion
            similar_columns = self._detect_similar_columns(intent, knowledge_data)
            
            # Step 3: Generate professional clarification questions
            clarification_questions = self._generate_clarification_questions(
                intent, knowledge_data, user_question, ambiguity_analysis, similar_columns
            )
            
            # Step 4: Determine if human approval is needed
            needs_approval = self._needs_human_approval(intent, ambiguity_analysis, similar_columns)
            
            if needs_approval:
                # Use LangGraph interrupt to pause workflow for human input
                approval_request = self._create_approval_request(
                    intent, knowledge_data, user_question, clarification_questions, similar_columns, ambiguity_analysis,
                    conversation_thread, conversation_history
                )
                
                return {
                    **state,
                    'human_approval_needed': True,
                    'approval_request': approval_request,
                    'clarification_questions': clarification_questions,
                    'similar_columns': similar_columns,
                    'ambiguity_analysis': ambiguity_analysis,
                    # This will trigger LangGraph interrupt
                    '__interrupt__': True
                }
            else:
                # No approval needed, proceed with intent
                return {
                    **state,
                    'intent': intent,  # CRITICAL FIX: Preserve the intent in state
                    'human_approval_needed': False,
                    'intent_approved': True,
                    'approval_reason': 'Intent is clear and unambiguous'
                }
                
        except Exception as e:
            print(f"[HumanApprovalAgent] Error: {e}")
            return {
                **state,
                'intent': state.get('intent', {}),  # CRITICAL FIX: Preserve the intent in state
                'human_approval_needed': False,
                'intent_approved': True,
                'approval_reason': f'Error in approval process: {e}'
            }
    
    def _analyze_intent_ambiguities(self, intent: Dict, knowledge_data: Dict, user_question: str) -> Dict:
        """
        Analyze intent for potential ambiguities that need human clarification.
        """
        ambiguities = {
            'has_multiple_tables': False,
            'has_multiple_columns': False,
            'has_ambiguous_filters': False,
            'has_ambiguous_aggregations': False,
            'confidence_issues': [],
            'potential_conflicts': []
        }
        
        # Check for multiple tables
        tables = intent.get('tables', [])
        if len(tables) > 1:
            ambiguities['has_multiple_tables'] = True
            ambiguities['potential_conflicts'].append(f"Multiple tables selected: {tables}")
        
        # Check for multiple columns
        columns = intent.get('columns', [])
        if len(columns) > 3:  # More than 3 columns might need clarification
            ambiguities['has_multiple_columns'] = True
            ambiguities['potential_conflicts'].append(f"Many columns selected: {len(columns)} columns")
        
        # Check for ambiguous filters
        filters = intent.get('filters', [])
        if len(filters) > 2:
            ambiguities['has_ambiguous_filters'] = True
            ambiguities['potential_conflicts'].append(f"Multiple filters: {filters}")
        
        # Check confidence scores
        confidence = intent.get('confidence', {})
        for key, score in confidence.items():
            if score < 0.7:  # Low confidence
                ambiguities['confidence_issues'].append(f"Low confidence in {key}: {score}")
        
        return ambiguities
    
    def _detect_similar_columns(self, intent: Dict, knowledge_data: Dict) -> List[Dict]:
        """
        Detect similar columns that might cause confusion.
        """
        similar_columns = []
        columns = intent.get('columns', [])
        schema = knowledge_data.get('schema', {})
        tables = schema.get('tables', {})
        
        # If no columns in intent, try to detect from filters
        if not columns:
            filters = intent.get('filters', [])
            for filter_expr in filters:
                # Extract column names from filter expressions using regex
                import re
                column_matches = re.findall(r'([A-Za-z_][A-Za-z0-9_]*)', filter_expr)
                
                if column_matches:
                    # Look for similar columns in the schema
                    for table_name, table_data in tables.items():
                        if isinstance(table_data, dict):
                            table_columns = table_data.get('columns', {})
                            
                            # Find columns that contain similar words to the filter column
                            similar_columns_found = self._find_similar_columns_by_pattern(
                                column_matches[0], table_columns, table_name
                            )
                            
                            if similar_columns_found:
                                similar_columns.extend(similar_columns_found)
                                break
        
        # Group columns by similarity
        for column in columns:
            # Find which table this column belongs to
            table_name = None
            for table, table_data in tables.items():
                if isinstance(table_data, dict):
                    table_columns = table_data.get('columns', {})
                    if column in table_columns:
                        table_name = table
                        break
            
            if table_name:
                # Get column metadata
                column_data = tables[table_name].get('columns', {}).get(column, {})
                
                # Check for similar columns in the same table
                similar_in_table = self._find_similar_columns_in_table(
                    column, table_name, tables[table_name], column_data
                )
                
                if similar_in_table:
                    similar_columns.append({
                        'original_column': column,
                        'table': table_name,
                        'similar_columns': similar_in_table,
                        'business_description': column_data.get('business_description', ''),
                        'business_terms': column_data.get('business_terms', [])
                    })
        
        return similar_columns
    
    def _find_similar_columns_by_pattern(self, target_column: str, table_columns: Dict, table_name: str) -> List[Dict]:
        """
        Find columns similar to the target column using pattern matching.
        This is a generic approach that doesn't hardcode specific words.
        """
        similar_columns = []
        
        # Extract meaningful words from the target column
        import re
        target_words = set(re.findall(r'[A-Za-z]+', target_column.lower()))
        
        # Find columns with overlapping words
        similar_candidates = []
        for col_name, col_data in table_columns.items():
            col_words = set(re.findall(r'[A-Za-z]+', col_name.lower()))
            
            # Calculate word overlap
            word_overlap = target_words & col_words
            if len(word_overlap) > 0 and col_name != target_column:
                similarity_score = len(word_overlap) * 5  # Base score for word overlap
                
                # Bonus for business terms overlap
                if isinstance(col_data, dict):
                    business_terms = col_data.get('business_terms', [])
                    if business_terms:
                        business_words = set([term.lower() for term in business_terms])
                        business_overlap = target_words & business_words
                        similarity_score += len(business_overlap) * 3
                
                similar_candidates.append({
                    'name': col_name,
                    'similarity_score': similarity_score,
                    'word_overlap': list(word_overlap),
                    'business_description': col_data.get('business_description', '') if isinstance(col_data, dict) else ''
                })
        
        # Sort by similarity score and take top candidates
        similar_candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Only return if we have multiple similar columns (indicating ambiguity)
        if len(similar_candidates) > 1:
            similar_columns.append({
                'original_column': target_column,
                'table': table_name,
                'similar_columns': similar_candidates[:5],  # Top 5 similar columns
                'business_description': f'Columns similar to {target_column}',
                'business_terms': list(target_words)
            })
        
        return similar_columns
    
    def _find_similar_columns_in_table(self, target_column: str, table_name: str, table_data: Dict, column_data: Dict) -> List[Dict]:
        """
        Find columns similar to the target column in the same table.
        """
        similar_columns = []
        columns = table_data.get('columns', {})
        
        # Get target column characteristics
        target_business_terms = column_data.get('business_terms', [])
        target_description = column_data.get('business_description', '').lower()
        target_name_parts = set(target_column.lower().split('_'))
        
        for col_name, col_info in columns.items():
            if col_name == target_column:
                continue
                
            similarity_score = 0
            reasons = []
            
            # Check business terms overlap
            col_business_terms = col_info.get('business_terms', [])
            term_overlap = set(target_business_terms) & set(col_business_terms)
            if term_overlap:
                similarity_score += 10
                reasons.append(f"Shared business terms: {list(term_overlap)}")
            
            # Check name similarity
            col_name_parts = set(col_name.lower().split('_'))
            name_overlap = target_name_parts & col_name_parts
            if name_overlap:
                similarity_score += 5
                reasons.append(f"Similar name parts: {list(name_overlap)}")
            
            # Check description similarity
            col_description = col_info.get('business_description', '').lower()
            if target_description and col_description:
                # Simple word overlap check
                target_words = set(target_description.split())
                col_words = set(col_description.split())
                word_overlap = target_words & col_words
                if len(word_overlap) > 2:  # More than 2 common words
                    similarity_score += 3
                    reasons.append(f"Similar descriptions: {list(word_overlap)}")
            
            # If similarity score is high enough, consider it similar
            if similarity_score >= 8:
                similar_columns.append({
                    'name': col_name,
                    'business_description': col_info.get('business_description', ''),
                    'business_terms': col_info.get('business_terms', []),
                    'similarity_score': similarity_score,
                    'reasons': reasons
                })
        
        # Sort by similarity score
        similar_columns.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similar_columns[:3]  # Return top 3 similar columns
    
    def _generate_clarification_questions(self, intent: Dict, knowledge_data: Dict, 
                                        user_question: str, ambiguity_analysis: Dict, 
                                        similar_columns: List[Dict]) -> List[Dict]:
        """
        Generate professional clarification questions for the user.
        """
        questions = []
        
        # Question 1: Intent confirmation
        intent_confirmation = self._generate_intent_confirmation_question(intent, knowledge_data)
        if intent_confirmation:
            questions.append(intent_confirmation)
        
        # Question 2: Similar columns clarification
        if similar_columns:
            column_clarification = self._generate_column_clarification_question(similar_columns)
            if column_clarification:
                questions.append(column_clarification)
        
        # Question 3: Business context clarification
        business_clarification = self._generate_business_clarification_question(intent, user_question)
        if business_clarification:
            questions.append(business_clarification)
        
        return questions
    
    def _generate_intent_confirmation_question(self, intent: Dict, knowledge_data: Dict) -> Optional[Dict]:
        """
        Generate a question to confirm the overall intent.
        """
        try:
            tables = intent.get('tables', [])
            columns = intent.get('columns', [])
            filters = intent.get('filters', [])
            aggregations = intent.get('aggregations', [])
            
            # Build business-friendly description
            business_description = self._build_business_description(intent, knowledge_data)
            
            question = {
                'id': 'intent_confirmation',
                'type': 'confirmation',
                'question': f"I understand you want to {business_description}. Is this correct?",
                'details': {
                    'tables': tables,
                    'columns': columns,
                    'filters': filters,
                    'aggregations': aggregations
                },
                'business_description': business_description
            }
            
            return question
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error generating intent confirmation: {e}")
            return None
    
    def _generate_column_clarification_question(self, similar_columns: List[Dict]) -> Optional[Dict]:
        """
        Generate a question to clarify similar columns.
        """
        try:
            if not similar_columns:
                return None
            
            # Build question text
            question_text = "I found some similar columns that might be relevant. Which one would you like me to use?\n\n"
            
            options = []
            for similar_group in similar_columns:
                original_col = similar_group['original_column']
                similar_cols = similar_group['similar_columns']
                
                # Add original column option
                options.append({
                    'id': f"original_{original_col}",
                    'name': original_col,
                    'description': similar_group['business_description'],
                    'type': 'original'
                })
                
                # Add similar column options
                for similar_col in similar_cols:
                    options.append({
                        'id': f"similar_{similar_col['name']}",
                        'name': similar_col['name'],
                        'description': similar_col['business_description'],
                        'type': 'similar',
                        'similarity_score': similar_col['similarity_score']
                    })
            
            question = {
                'id': 'column_clarification',
                'type': 'choice',
                'question': question_text,
                'options': options,
                'similar_columns': similar_columns
            }
            
            return question
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error generating column clarification: {e}")
            return None
    
    def _generate_business_clarification_question(self, intent: Dict, user_question: str) -> Optional[Dict]:
        """
        Generate a business context clarification question.
        """
        try:
            # Analyze what business context might be missing
            business_context_needed = []
            
            # Check if time range is specified
            if not intent.get('time_range'):
                business_context_needed.append('time period')
            
            # Check if specific criteria are mentioned
            filters = intent.get('filters', [])
            if not filters:
                business_context_needed.append('specific criteria')
            
            # Check if aggregation level is clear
            aggregations = intent.get('aggregations', [])
            if not aggregations and any(word in user_question.lower() for word in ['total', 'average', 'count', 'sum']):
                business_context_needed.append('aggregation level')
            
            if business_context_needed:
                question_text = f"To provide you with the most accurate results, could you clarify the following: {', '.join(business_context_needed)}?"
                
                question = {
                    'id': 'business_clarification',
                    'type': 'clarification',
                    'question': question_text,
                    'missing_context': business_context_needed
                }
                
                return question
            
            return None
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error generating business clarification: {e}")
            return None
    
    def _build_business_description(self, intent: Dict, knowledge_data: Dict) -> str:
        """
        Build a business-friendly description of the intent.
        """
        try:
            tables = intent.get('tables', [])
            columns = intent.get('columns', [])
            filters = intent.get('filters', [])
            aggregations = intent.get('aggregations', [])
            
            print(f"[HumanApprovalAgent] Building business description for tables: {tables}")
            print(f"[HumanApprovalAgent] Building business description for columns: {columns}")
            
            # Get business context from schema
            schema = knowledge_data.get('schema', {})
            schema_tables = schema.get('tables', {})
            
            print(f"[HumanApprovalAgent] Schema tables available: {list(schema_tables.keys()) if schema_tables else 'None'}")
            print(f"[HumanApprovalAgent] Using updated schema: {bool(schema_tables)}")
            
            # Build table descriptions
            table_descriptions = []
            for table in tables:
                table_data = schema_tables.get(table, {})
                business_context = table_data.get('business_context', '')
                if business_context:
                    print(f"[HumanApprovalAgent] Using business context for table '{table}': {business_context}")
                    table_descriptions.append(business_context)
                else:
                    print(f"[HumanApprovalAgent] No business context found for table '{table}', using fallback")
                    table_descriptions.append(f"data from {table}")
            
            # Build column descriptions
            column_descriptions = []
            for column in columns:
                # Find column in schema
                for table_name, table_data in schema_tables.items():
                    if isinstance(table_data, dict):
                        table_columns = table_data.get('columns', {})
                        if column in table_columns:
                            col_data = table_columns[column]
                            business_desc = col_data.get('business_description', '')
                            if business_desc:
                                print(f"[HumanApprovalAgent] Using business description for column '{column}': {business_desc}")
                                column_descriptions.append(business_desc)
                            else:
                                print(f"[HumanApprovalAgent] No business description found for column '{column}', using fallback")
                                column_descriptions.append(column)
                            break
            
            # Build the description
            description_parts = []
            
            if table_descriptions:
                description_parts.append(f"analyze {', '.join(table_descriptions)}")
            
            if column_descriptions:
                description_parts.append(f"focusing on {', '.join(column_descriptions)}")
            
            if filters:
                description_parts.append(f"with specific criteria: {', '.join(filters)}")
            
            if aggregations:
                description_parts.append(f"including calculations: {', '.join(aggregations)}")
            
            if description_parts:
                final_description = ' '.join(description_parts)
                print(f"[HumanApprovalAgent] Final business description: {final_description}")
                return final_description
            else:
                print(f"[HumanApprovalAgent] No description parts found, using fallback")
                return "retrieve data from the database"
                
        except Exception as e:
            print(f"[HumanApprovalAgent] Error building business description: {e}")
            return "retrieve data from the database"
    
    def _needs_human_approval(self, intent: Dict, ambiguity_analysis: Dict, similar_columns: List[Dict]) -> bool:
        """
        Determine if human approval is needed. The primary trigger is ambiguity in column selection.
        """
        print(f"[HumanApprovalAgent] Analyzing if human approval is needed...")
        selected_columns = intent.get('columns', [])
        user_question = intent.get('user_question', '')
        
        # SMART AMBIGUITY DETECTION: Not all multiple columns indicate ambiguity
        if len(selected_columns) > 1:
            # Check if this is logical necessity (e.g., "which vendors have high CPIScore?" needs both CPIScore and VendorName)
            if self._is_logical_necessity(selected_columns, user_question):
                print(f"[HumanApprovalAgent] Multiple columns are logically necessary for the query. No ambiguity detected.")
                return False
            else:
                print(f"[HumanApprovalAgent] CRITICAL: Intent Picker returned multiple columns ({selected_columns}) indicating true ambiguity. Requesting human approval.")
                return True
        
        # SECONDARY RULE: Check for low confidence from the LLM as a fallback.
        confidence = intent.get('confidence', {})
        column_confidence = confidence.get('columns', 1.0)
        if column_confidence < 0.75:
            print(f"[HumanApprovalAgent] Low column confidence detected ({column_confidence}). Requesting human approval.")
            return True
        
        # If we get here, the Intent Picker found a single, confident match.
        print(f"[HumanApprovalAgent] Intent is clear and unambiguous. Proceeding without approval.")
        return False
    
    def _is_logical_necessity(self, columns: List[str], user_question: str) -> bool:
        """
        Determine if multiple columns are logically necessary for the query (not ambiguity).
        Examples:
        - "which entities have attributes?" → needs attribute + entity identifier (logical necessity)
        - "show me scores" → could be multiple types of scores (ambiguity)
        - "are X linked to Y?" → needs both X and Y variables (logical necessity)
        """
        question_lower = user_question.lower()
        
        # Patterns that indicate logical necessity (not ambiguity)
        logical_necessity_patterns = [
            # "which [entities] have [attribute]?" → needs both the attribute and entity identifier
            (r'which\s+\w+\s+have', ['name', 'id', 'number']),  # which entities have attributes
            (r'which\s+\w+\s+are', ['name', 'id', 'number']),   # which entities are something
            (r'which\s+\w+\s+show', ['name', 'id', 'number']),  # which entities show something
            
            # "list [entities] with [attribute]" → needs both
            (r'list\s+\w+\s+with', ['name', 'id', 'number']),
            (r'show\s+\w+\s+with', ['name', 'id', 'number']),
            
            # Relationship analysis patterns → needs both variables being compared
            (r'are\s+.*\s+linked\s+to', []),  # are entities linked to other entities
            (r'do\s+.*\s+correlate\s+with', []),  # do variables correlate with other variables
            (r'is\s+there\s+a\s+relationship', []),  # is there a relationship between variables
            (r'are\s+.*\s+associated\s+with', []),  # are variables associated with others
        ]
        
        # Check if the question asks for entities with attributes or relationship analysis
        for pattern, identifier_columns in logical_necessity_patterns:
            if re.search(pattern, question_lower):
                # For relationship analysis patterns, check if we have both variables being compared
                if any(rel_pattern in pattern for rel_pattern in ['linked', 'correlate', 'relationship', 'associated']):
                    # Relationship analysis: need both variables - check if columns represent different concepts
                    # This is a relationship question, so having 2 columns is logical necessity
                    if len(columns) == 2:
                        print(f"[HumanApprovalAgent] Detected logical necessity: relationship analysis question needs both variables being compared.")
                        return True
                else:
                    # Entity-attribute patterns: check if we have both metric and identifier
                    # Look for common patterns: one column for the metric/attribute, one for the entity identifier
                    has_identifier = any(col.lower() in identifier_columns or 'name' in col.lower() or 'id' in col.lower() or 'number' in col.lower() for col in columns)
                    
                    # If we have an identifier column and this is an entity-attribute question, it's likely logical necessity
                    if has_identifier and len(columns) == 2:
                        print(f"[HumanApprovalAgent] Detected logical necessity: entity-attribute question with identifier column.")
                        return True
        
        # Check for specific patterns that are clearly logical necessity
        if 'which' in question_lower and ('have' in question_lower or 'are' in question_lower):
            # "which X have Y" or "which X are Y" typically needs both X identifier and Y attribute
            if len(columns) == 2:
                print(f"[HumanApprovalAgent] Detected logical necessity: 'which X have Y' pattern with 2 columns.")
                return True
        
        # Check for relationship analysis patterns
        relationship_keywords = ['linked', 'correlate', 'relationship', 'associated', 'connected', 'between']
        found_keywords = [keyword for keyword in relationship_keywords if keyword in question_lower]
        if found_keywords:
            print(f"[HumanApprovalAgent] Found relationship keywords: {found_keywords}")
            # Relationship analysis typically needs both variables being compared
            if len(columns) == 2:
                print(f"[HumanApprovalAgent] Detected logical necessity: relationship analysis pattern with 2 columns.")
                return True
        
        # Check for percentage/ratio analysis patterns
        percentage_keywords = ['percentage', 'percent', '%', 'ratio', 'proportion', 'breakdown', 'distribution', 'vs', 'versus', 'by', 'across']
        found_percentage_keywords = [keyword for keyword in percentage_keywords if keyword in question_lower]
        if found_percentage_keywords:
            print(f"[HumanApprovalAgent] Found percentage/ratio keywords: {found_percentage_keywords}")
            # Percentage/ratio analysis typically needs both the metric and the breakdown dimension
            if len(columns) == 2:
                print(f"[HumanApprovalAgent] Detected logical necessity: percentage/ratio analysis pattern with 2 columns.")
                return True
        
        # If we get here, it's likely true ambiguity
        print(f"[HumanApprovalAgent] Multiple columns appear to be ambiguous rather than logically necessary.")
        return False
    
    def _generate_contextual_message(self, intent: Dict, user_question: str, 
                                   similar_columns: List[Dict], ambiguity_analysis: Dict, 
                                   business_description: str) -> str:
        """
        Generate dynamic, contextual approval messages based on the specific situation.
        Enhanced to handle multiple column ambiguity with descriptions.
        """
        try:
            # Extract key information
            tables = intent.get('tables', [])
            columns = intent.get('columns', [])
            filters = intent.get('filters', [])
            aggregations = intent.get('aggregations', [])
            
            # NEW: Handle multiple columns from Intent Picker (primary case)
            if len(columns) > 1:
                # This is the main case - Intent Picker found multiple potential columns
                # We need to present them with their descriptions for user choice
                return self._generate_multiple_column_choice_message(columns, user_question, intent)
            
            # Determine the primary issue that triggered approval
            elif similar_columns:
                # Similar columns issue
                original_column = similar_columns[0]['original_column'] if similar_columns else 'the column'
                similar_count = len(similar_columns[0]['similar_columns']) if similar_columns else 0
                
                if similar_count == 1:
                    similar_name = similar_columns[0]['similar_columns'][0]['name']
                    message = f"I found a similar column '{similar_name}' that might be what you're looking for instead of '{original_column}'. Which one would you prefer?"
                elif similar_count == 2:
                    similar_names = [col['name'] for col in similar_columns[0]['similar_columns']]
                    message = f"I found two similar columns ({', '.join(similar_names)}) that could match your request for '{original_column}'. Which one should I use?"
                else:
                    similar_names = [col['name'] for col in similar_columns[0]['similar_columns']]
                    message = f"I found {similar_count} similar columns ({', '.join(similar_names[:2])}{'...' if similar_count > 2 else ''}) that could be relevant to your question about '{original_column}'. Which one would you like me to use?"
            
            elif ambiguity_analysis.get('has_multiple_tables'):
                # Multiple tables issue
                table_names = ', '.join(tables)
                message = f"Your request involves multiple tables ({table_names}). I want to make sure I'm joining them correctly. Could you clarify the relationship between these tables?"
            
            elif ambiguity_analysis.get('has_multiple_columns'):
                # Many columns issue
                column_count = len(columns)
                message = f"You're asking for {column_count} columns, which is quite comprehensive. To ensure I'm not missing anything important, could you confirm if you need all of these columns or if there are specific ones you're most interested in?"
            
            elif ambiguity_analysis.get('has_ambiguous_filters'):
                # Complex filters issue
                filter_count = len(filters)
                message = f"Your request has {filter_count} different filter conditions. I want to make sure I understand the logic correctly. Could you help me clarify how these filters should work together?"
            
            elif ambiguity_analysis.get('confidence_issues'):
                # Low confidence issue
                confidence_issues = ambiguity_analysis.get('confidence_issues', [])
                if 'table' in str(confidence_issues).lower():
                    message = f"I'm not entirely sure which table contains the data you're looking for. Could you help me understand which table would be most appropriate?"
                elif 'column' in str(confidence_issues).lower():
                    message = f"I'm not completely confident about which column to use for your request. Could you help me identify the right one?"
                else:
                    message = f"I want to make sure I understand your request correctly. Could you help me clarify a few details to ensure I provide exactly what you need?"
            
            elif aggregations:
                # Aggregation issue
                agg_types = [agg.split('(')[0] for agg in aggregations]
                message = f"You're asking for {', '.join(agg_types)} calculations. I want to make sure I'm calculating these correctly. Could you confirm the aggregation level you need?"
            
            else:
                # Generic approval request
                if 'payment' in user_question.lower():
                    message = f"I understand you want to analyze payment data. Before I proceed, I'd like to confirm a few details to ensure I get exactly what you need."
                elif 'customer' in user_question.lower():
                    message = f"I understand you want to analyze customer data. Let me confirm a few details to ensure I provide the most relevant information."
                elif 'sales' in user_question.lower():
                    message = f"I understand you want to analyze sales data. I'd like to confirm a few details to ensure I calculate the metrics correctly."
                else:
                    message = f"I understand you want to {business_description}. Before I proceed, I'd like to confirm a few details to ensure I get exactly what you need."
            
            return message
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error generating contextual message: {e}")
            # Fallback to generic message
            return f"I understand you want to {business_description}. Before I proceed, I'd like to confirm a few details to ensure I get exactly what you need."
    
    def _generate_multiple_column_choice_message(self, columns: List[str], user_question: str, intent: Dict) -> str:
        """
        Generate a multiple-choice message when Intent Picker found multiple potential columns.
        This is the core of the new description-driven approach.
        """
        try:
            # Get the knowledge data from the state (not from intent)
            # The intent doesn't contain knowledge_data, we need to get it from the state
            print(f"🔍 GENERATING MULTIPLE CHOICE for columns: {columns}")
            print(f"🔍 Intent keys: {list(intent.keys())}")
            
            # Try to get schema from the state that was passed to this agent
            # The schema should be available in the agent's context
            knowledge_data = getattr(self, '_current_knowledge_data', {})
            if not knowledge_data:
                # Fallback: try to get from intent
                knowledge_data = intent.get('knowledge_data', {})
            
            schema = knowledge_data.get('schema', {})
            tables = schema.get('tables', {})
            
            print(f"🔍 Schema keys: {list(schema.keys())}")
            print(f"🔍 Tables keys: {list(tables.keys())}")
            
            # Build the choice message
            message_parts = [
                f"I found multiple columns that could match your question: \"{user_question}\"",
                "",
                "Please choose which column you'd like me to use:",
                ""
            ]
            
            # Add each column option with its description
            for i, column_name in enumerate(columns, 1):
                # Find the column in the schema to get its description
                column_description = self._get_column_description(column_name, tables)
                
                message_parts.append(f"{i}. {column_name}")
                if column_description:
                    message_parts.append(f"   Description: {column_description}")
                message_parts.append("")
            
            message_parts.append("Please respond with the number (1, 2, etc.) of your choice.")
            
            return "\n".join(message_parts)
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error generating multiple column choice: {e}")
            # Fallback message
            return f"I found multiple columns that could match your question: {', '.join(columns)}. Please specify which one you'd like me to use."
    
    def _get_column_description(self, column_name: str, tables: Dict) -> str:
        """
        Get the description of a column from the schema.
        Enhanced to handle the same schema structure as Intent Picker.
        """
        try:
            print(f"🔍 GETTING DESCRIPTION for column: {column_name}")
            print(f"🔍 Available tables: {list(tables.keys())}")
            
            for table_name, table_data in tables.items():
                if isinstance(table_data, dict):
                    columns = table_data.get('columns', {})
                    print(f"🔍 Table {table_name} has {len(columns)} columns")
                    print(f"🔍 Column names: {list(columns.keys())[:10]}...")  # Show first 10
                    
                    if column_name in columns:
                        col_data = columns[column_name]
                        if isinstance(col_data, dict):
                            print(f"🔍 FOUND COLUMN DATA for {column_name}: {col_data}")
                            
                            # Get description (primary business context)
                            description = col_data.get('description', '')
                            if description:
                                print(f"✅ FOUND DESCRIPTION: {column_name} -> {description}")
                                return description
                            else:
                                print(f"⚠️  NO DESCRIPTION for {column_name}")
                            
                            # Fallback to business_terms if no description
                            business_terms = col_data.get('business_terms', [])
                            if business_terms:
                                print(f"✅ FOUND BUSINESS TERMS: {column_name} -> {business_terms}")
                                return f"Business terms: {', '.join(business_terms)}"
                            
                            # Fallback to use_cases
                            use_cases = col_data.get('use_cases', [])
                            if use_cases:
                                print(f"✅ FOUND USE CASES: {column_name} -> {use_cases}")
                                return f"Use cases: {', '.join(use_cases)}"
                            
                            print(f"⚠️  NO CONTEXT FIELDS for {column_name}")
                    else:
                        print(f"⚠️  Column {column_name} not found in table {table_name}")
            
            print(f"⚠️  COLUMN NOT FOUND: {column_name}")
            return "No description available"
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error getting column description: {e}")
            return "No description available"
    
    def _create_approval_request(self, intent: Dict, knowledge_data: Dict, 
                               user_question: str, clarification_questions: List[Dict], 
                               similar_columns: List[Dict], ambiguity_analysis: Dict,
                               conversation_thread: str, conversation_history: List[Dict]) -> Dict:
        """
        Create a comprehensive approval request for the user.
        """
        try:
            # Build business description
            business_description = self._build_business_description(intent, knowledge_data)
            
            # Generate dynamic, contextual message based on the specific situation
            message = self._generate_contextual_message(
                intent, user_question, similar_columns, ambiguity_analysis, business_description
            )
            
            # Create the approval request with conversation threading
            approval_request = {
                'message': message,
                'intent_summary': {
                    'tables': intent.get('tables', []),
                    'columns': intent.get('columns', []),
                    'filters': intent.get('filters', []),
                    'aggregations': intent.get('aggregations', []),
                    'business_description': business_description
                },
                'clarification_questions': clarification_questions,
                'similar_columns': similar_columns,
                'requires_human_input': True,
                'approval_type': 'intent_confirmation',
                'conversation_thread': conversation_thread,
                'original_question': user_question,
                'conversation_history': conversation_history
            }
            
            return approval_request
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error creating approval request: {e}")
            return {
                'message': "I need to confirm some details before proceeding with your request.",
                'requires_human_input': True,
                'approval_type': 'intent_confirmation'
            }
    
    def handle_human_response(self, state: Dict[str, Any], human_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle human response to approval request.
        """
        try:
            response_type = human_response.get('type', 'approval')
            
            # Log conversation threading
            conversation_thread = human_response.get('conversation_thread', 'unknown')
            original_question = human_response.get('original_question', 'unknown')
            print(f"[HumanApprovalAgent] Handling response for thread: {conversation_thread}")
            print(f"[HumanApprovalAgent] Original question: {original_question}")
            print(f"[HumanApprovalAgent] Response type: {response_type}")
            
            if response_type == 'approval':
                # User approved the intent
                return {
                    **state,
                    'human_approval_needed': False,
                    'intent_approved': True,
                    'approval_reason': 'User approved intent',
                    'human_response': human_response
                }
            
            elif response_type == 'clarification':
                # User provided clarification
                clarified_intent = self._process_clarification_response(state, human_response)
                return {
                    **state,
                    'intent': clarified_intent,
                    'human_approval_needed': False,
                    'intent_approved': True,
                    'approval_reason': 'User provided clarification',
                    'human_response': human_response
                }
            
            elif response_type == 'modification':
                # User wants to modify the intent
                modified_intent = self._process_modification_response(state, human_response)
                return {
                    **state,
                    'intent': modified_intent,
                    'human_approval_needed': False,
                    'intent_approved': True,
                    'approval_reason': 'User modified intent',
                    'human_response': human_response
                }
            
            else:
                # Unknown response type, default to approval
                return {
                    **state,
                    'human_approval_needed': False,
                    'intent_approved': True,
                    'approval_reason': 'User response processed',
                    'human_response': human_response
                }
                
        except Exception as e:
            print(f"[HumanApprovalAgent] Error handling human response: {e}")
            return {
                **state,
                'human_approval_needed': False,
                'intent_approved': True,
                'approval_reason': f'Error processing response: {e}',
                'human_response': human_response
            }
    
    def _process_clarification_response(self, state: Dict[str, Any], human_response: Dict[str, Any]) -> Dict:
        """
        Process user clarification and update intent accordingly.
        """
        try:
            intent = state.get('intent', {}).copy()
            clarifications = human_response.get('clarifications', {})
            
            # Update tables if specified
            if 'tables' in clarifications:
                intent['tables'] = clarifications['tables']
            
            # Update columns if specified
            if 'columns' in clarifications:
                intent['columns'] = clarifications['columns']
            
            # Update filters if specified
            if 'filters' in clarifications:
                intent['filters'] = clarifications['filters']
            
            # Update aggregations if specified
            if 'aggregations' in clarifications:
                intent['aggregations'] = clarifications['aggregations']
            
            # Update time range if specified
            if 'time_range' in clarifications:
                intent['time_range'] = clarifications['time_range']
            
            # Update sorting if specified
            if 'sorting' in clarifications:
                intent['sorting'] = clarifications['sorting']
            
            return intent
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error processing clarification: {e}")
            return state.get('intent', {})
    
    def _process_modification_response(self, state: Dict[str, Any], human_response: Dict[str, Any]) -> Dict:
        """
        Process user modifications to intent.
        """
        try:
            # Create new intent based on user modifications
            modified_intent = human_response.get('modified_intent', {})
            
            if modified_intent:
                return modified_intent
            else:
                # Fallback to original intent
                return state.get('intent', {})
                
        except Exception as e:
            print(f"[HumanApprovalAgent] Error processing modification: {e}")
            return state.get('intent', {})
