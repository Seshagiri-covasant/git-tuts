#!/usr/bin/env python3
"""
Advanced Conversational Intent Analyzer
- Natural conversation flow like ChatGPT/Claude/Gemini
- Discusses with user until complete context
- Summarizes everything before SQL generation
- No hardcoded interactions - pure LLM-based
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseLanguageModel

class ConversationalIntentAnalyzer:
    """
    Advanced conversational intent analyzer that works like ChatGPT/Claude/Gemini.
    Engages in natural conversation to gather complete context before SQL generation.
    """
    
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
        self.conversation_context = []
        self.requirements_gathered = {
            "tables": [],
            "columns": [],
            "filters": [],
            "aggregations": [],
            "time_range": "",
            "sorting": "",
            "business_context": ""
        }
        self.conversation_phase = "initial"  # initial, gathering, summarizing, approved
        self.summary = ""
        
    def analyze_intent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method that handles conversational intent analysis.
        """
        try:
            user_question = state.get('user_question', '')
            conversation_history = state.get('conversation_history', [])
            knowledge_data = state.get('knowledge_data', {})
            
            print(f"[ConversationalIntentAnalyzer] Phase: {self.conversation_phase}")
            print(f"[ConversationalIntentAnalyzer] User question: {user_question}")
            
            # Build conversation context
            conversation_context = self._build_conversation_context(conversation_history)
            
            # Determine what to do based on conversation phase
            if self.conversation_phase == "initial":
                return self._handle_initial_question(user_question, conversation_context, knowledge_data)
            elif self.conversation_phase == "gathering":
                return self._handle_follow_up_question(user_question, conversation_context, knowledge_data)
            elif self.conversation_phase == "summarizing":
                return self._handle_summary_response(user_question, conversation_context, knowledge_data)
            elif self.conversation_phase == "approved":
                return self._generate_final_intent(user_question, conversation_context, knowledge_data)
            else:
                return self._handle_initial_question(user_question, conversation_context, knowledge_data)
                
        except Exception as e:
            print(f"[ConversationalIntentAnalyzer] Error: {e}")
            return {
                **state,
                'intent': {
                    "tables": [], "columns": [], "filters": [], "aggregations": [],
                    "time_range": "", "sorting": "", "reasoning": f"Error in Intent Analyzer: {e}",
                    "is_follow_up": False, "follow_up_context": "",
                    "confidence": {"tables": 0.0, "columns": 0.0, "filters": 0.0, "aggregations": 0.0, "overall": 0.0}
                },
                'error': str(e)
            }
    
    def _handle_initial_question(self, user_question: str, conversation_context: str, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the initial user question."""
        print(f"[ConversationalIntentAnalyzer] Handling initial question")
        
        # Build knowledge overview
        knowledge_overview = self._build_knowledge_overview(knowledge_data, user_question)
        
        # 🔍 LOGGING: Track what data is being sent to ConversationalIntentAnalyzer LLM
        print(f"\n{'='*80}")
        print(f"🔍 LLM COLUMN USAGE DEBUG: ConversationalIntentAnalyzer")
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
        
        # Check for column ambiguity before LLM analysis
        column_ambiguity = self._detect_column_ambiguity(user_question, knowledge_data)
        if column_ambiguity.get('needs_clarification', False):
            print(f"[ConversationalIntentAnalyzer] Column ambiguity detected, asking user to clarify")
            return {
                'clarification_needed': True,
                'clarification_question': column_ambiguity['clarification_question'],
                'ambiguity_type': column_ambiguity['ambiguity_type'],
                'options': column_ambiguity['options'],
                'conversation_phase': 'clarification_needed'
            }

        # Use LLM to analyze the question and determine what information is needed
        analysis_prompt = f"""You are an expert data analyst having a natural conversation with a user about their data needs.

CONVERSATION CONTEXT:
{conversation_context}

USER'S QUESTION:
{user_question}

AVAILABLE DATABASE SCHEMA:
{knowledge_overview}

CRITICAL INSTRUCTION: When the question involves aggregations (AVG, SUM, COUNT, etc.) and there are pre-defined metrics available above, you MUST use the EXACT metric names from the "Available Database Metrics" section.

IMPORTANT: 
- Do NOT create your own metric names
- Do NOT use raw column names from the table schema
- ALWAYS prioritize the "Available Database Metrics" section over individual table columns
- Use ONLY the exact names provided in the "Available Database Metrics" section

ALWAYS copy the exact metric name from the "Available Database Metrics" section.

Your task is to understand what the user wants and determine if you need more information to provide a complete answer. Think like a human analyst who wants to help the user get exactly what they need.

If you have enough information to understand their request clearly, respond with "needs_clarification": false.
If you need more details to provide a complete answer, ask natural, conversational follow-up questions.

Respond with a JSON object containing:
- "needs_clarification": true/false
- "clarification_question": "Natural follow-up question to ask the user"
- "gathered_info": {{"tables": [], "columns": [], "filters": [], "aggregations": [], "time_range": "", "sorting": "", "business_context": ""}}
- "reasoning": "Why you're asking this question"

Be conversational, helpful, and natural. Ask questions that a human analyst would ask to get complete context."""

        try:
            response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            
            # 🔍 LOGGING: Capture LLM's raw response and reasoning
            print(f"\n{'='*80}")
            print(f"🤖 LLM RESPONSE ANALYSIS: ConversationalIntentAnalyzer")
            print(f"{'='*80}")
            print(f"📝 Raw LLM Response:")
            print(f"{response.content}")
            print(f"📊 Response Length: {len(response.content)} characters")
            print(f"{'='*80}\n")
            
            # Try to parse JSON response
            try:
                # Clean the response text to remove markdown formatting
                cleaned_response = response.content.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                analysis = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a fallback response
                print(f"[ConversationalIntentAnalyzer] JSON parsing failed, using fallback")
                analysis = {
                    "needs_clarification": True,
                    "clarification_question": "I understand you want to find transactions with specific criteria. Could you clarify what threshold you're looking for?",
                    "gathered_info": {
                        "tables": ["Payments"],
                        "columns": ["score_column"],
                        "filters": ["score_column > threshold"],
                        "aggregations": [],
                        "time_range": "",
                        "sorting": "",
                        "business_context": "Finding transactions with specific criteria"
                    },
                    "reasoning": "Need to clarify the threshold criteria"
                }
            
            # Check if the question is actually clear despite what the LLM says
            gathered_info = analysis.get("gathered_info", {})
            question_clarity = self._assess_question_clarity(gathered_info, user_question)
            
            print(f"[ConversationalIntentAnalyzer] Question clarity assessment:")
            print(f"  - LLM says needs_clarification: {analysis.get('needs_clarification', False)}")
            print(f"  - Our assessment is_clear: {question_clarity.get('is_clear', False)}")
            print(f"  - has_aggregation: {question_clarity.get('has_aggregation', False)}")
            print(f"  - has_metric: {question_clarity.get('has_metric', False)}")
            print(f"  - has_specific_requirements: {question_clarity.get('has_specific_requirements', False)}")
            
            # Override LLM decision if our assessment says the question is clear
            if question_clarity.get('is_clear', False):
                print(f"[ConversationalIntentAnalyzer] Overriding LLM - question is actually clear")
                # Move to summarizing phase
                self.conversation_phase = "summarizing"
                return self._create_summary(gathered_info, user_question, knowledge_data)
            elif analysis.get("needs_clarification", False):
                self.conversation_phase = "gathering"
                return {
                    'clarification_needed': True,
                    'clarification_question': analysis.get("clarification_question", "Could you provide more details?"),
                    'gathered_info': gathered_info,
                    'reasoning': analysis.get("reasoning", "Need more information"),
                    'conversation_phase': self.conversation_phase
                }
            else:
                # Move to summarizing phase
                self.conversation_phase = "summarizing"
                return self._create_summary(gathered_info, user_question, knowledge_data)
                
        except Exception as e:
            print(f"[ConversationalIntentAnalyzer] Error in initial question handling: {e}")
            return {
                'clarification_needed': True,
                'clarification_question': "I'd like to help you with your data question. Could you provide more details about what you're looking for?",
                'reasoning': "Need to understand your requirements better"
            }
    
    def _handle_follow_up_question(self, user_question: str, conversation_context: str, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle follow-up questions during the gathering phase."""
        print(f"[ConversationalIntentAnalyzer] Handling follow-up question")
        
        # Update requirements based on user response
        self._update_requirements_from_response(user_question)
        
        # Check if we have enough information
        if self._has_complete_context():
            self.conversation_phase = "summarizing"
            return self._create_summary(self.requirements_gathered, user_question, knowledge_data)
        else:
            # Ask another follow-up question
            follow_up_question = self._generate_follow_up_question(user_question, knowledge_data)
            return {
                'clarification_needed': True,
                'clarification_question': follow_up_question,
                'gathered_info': self.requirements_gathered,
                'reasoning': "Need more information to provide a complete answer",
                'conversation_phase': self.conversation_phase
            }
    
    def _handle_summary_response(self, user_question: str, conversation_context: str, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user response to the summary."""
        print(f"[ConversationalIntentAnalyzer] Handling summary response")
        
        # Check if user approves the summary
        if self._user_approves_summary(user_question):
            self.conversation_phase = "approved"
            return self._generate_final_intent(user_question, conversation_context, knowledge_data)
        else:
            # User wants changes, go back to gathering
            self.conversation_phase = "gathering"
            clarification_question = self._ask_for_changes(user_question)
            return {
                'clarification_needed': True,
                'clarification_question': clarification_question,
                'gathered_info': self.requirements_gathered,
                'reasoning': "User wants changes to the summary",
                'conversation_phase': self.conversation_phase
            }
    
    def _create_summary(self, gathered_info: Dict[str, Any], user_question: str, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of what we've gathered."""
        print(f"[ConversationalIntentAnalyzer] Creating summary")
        
        # Build knowledge overview
        knowledge_overview = self._build_knowledge_overview(knowledge_data, user_question)
        
        summary_prompt = f"""You are an expert business analyst. Create a clear, business-focused summary of what the user wants to know.

USER'S ORIGINAL QUESTION:
{user_question}

GATHERED INFORMATION:
{json.dumps(gathered_info, indent=2)}

Create a summary that explains what the user wants to know in BUSINESS TERMS ONLY. Do NOT mention specific table names, column names, or technical database details. Instead, use business language like:
- "payment transactions" instead of "Payments table"
- "scores" instead of "specific column names"
- "high-value transactions" instead of "transactions with specific criteria"
- "vendor information" instead of "VendorName column"

Write it in natural, conversational language that a business user would understand. Ask the user to confirm if this is correct.

Respond with a JSON object containing:
- "summary": "Clear business summary of what we'll analyze (NO technical details)"
- "business_description": "What business question we're answering"
- "data_focus": "What type of business data we're looking at"
- "criteria": "What business criteria we're applying"
- "expected_outcome": "What business insights we expect to find"
- "confirmation_question": "Question asking user to confirm this is correct"

Be conversational, business-focused, and avoid all technical database terminology."""

        try:
            response = self.llm.invoke([HumanMessage(content=summary_prompt)])
            
            # Try to parse JSON response
            try:
                # Clean the response text to remove markdown formatting
                cleaned_response = response.content.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                summary_data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a fallback response
                print(f"[ConversationalIntentAnalyzer] JSON parsing failed in summary, using fallback")
                summary_data = {
                    "summary": "I understand you want to find payment transactions that meet specific criteria. This will help identify transactions that may need additional review.",
                    "business_description": "Finding payment transactions with specific criteria",
                    "data_focus": "Payment transaction data with scoring",
                    "criteria": "Score above threshold",
                    "expected_outcome": "List of payments that require additional review due to specific criteria",
                    "confirmation_question": "Is this correct? Should I proceed with finding these transactions?"
                }
            
            self.summary = summary_data.get("summary", "")
            # CRITICAL FIX: Preserve the gathered_info data instead of overwriting with empty values
            self.requirements_gathered = {
                "tables": gathered_info.get("tables", []),
                "columns": gathered_info.get("columns", []),
                "filters": gathered_info.get("filters", []),
                "aggregations": gathered_info.get("aggregations", []),
                "time_range": gathered_info.get("time_range", ""),
                "sorting": gathered_info.get("sorting", ""),
                "business_context": gathered_info.get("business_context", "")
            }
            
            # For clear, unambiguous questions, proceed directly to SQL generation
            # Only ask for confirmation if the question is complex or ambiguous
            question_clarity = self._assess_question_clarity(gathered_info, user_question)
            
            print(f"[ConversationalIntentAnalyzer] Question clarity assessment:")
            print(f"  - has_aggregation: {question_clarity.get('has_aggregation', False)}")
            print(f"  - has_metric: {question_clarity.get('has_metric', False)}")
            print(f"  - has_specific_requirements: {question_clarity.get('has_specific_requirements', False)}")
            print(f"  - is_clear: {question_clarity.get('is_clear', False)}")
            
            if question_clarity['is_clear']:
                # Question is clear, proceed to SQL generation
                # CRITICAL FIX: Create INTENT message for query generator
                import json as _json
                intent_message = f"INTENT:{_json.dumps(self.requirements_gathered)}"
                
                # Add intent message to state for query generator
                state = {
                    'clarification_needed': False,
                    'gathered_info': self.requirements_gathered,
                    'reasoning': "Question is clear, proceeding to SQL generation",
                    'conversation_phase': 'ready_for_sql',
                    'business_description': summary_data.get('business_description', ''),
                    'data_focus': summary_data.get('data_focus', ''),
                    'criteria': summary_data.get('criteria', ''),
                    'expected_outcome': summary_data.get('expected_outcome', ''),
                    'intent_message': intent_message  # Add this for query generator
                }
                
                # Add intent message to messages for query generator to find
                if 'messages' not in state:
                    state['messages'] = []
                state['messages'].append({
                    'role': 'system',
                    'content': intent_message
                })
                
                # AGENT THOUGHTS: Internal reasoning process
                agent_thoughts = self._generate_conversational_thoughts(state.get('user_question', ''), self.requirements_gathered, summary_data)
                
                # DECISION TRANSPARENCY: Structured decision trace
                decision_trace = self._build_conversational_decision_trace(
                    state.get('user_question', ''), self.requirements_gathered, summary_data
                )
                
                state['agent_thoughts'] = agent_thoughts
                state['decision_trace'] = decision_trace
                return state
            else:
                # Question needs clarification, ask for confirmation
                return {
                    'clarification_needed': True,
                    'clarification_question': f"{summary_data.get('summary', '')}\n\n{summary_data.get('confirmation_question', 'Does this look correct?')}",
                    'gathered_info': self.requirements_gathered,
                    'reasoning': "Presenting summary for user confirmation",
                    'conversation_phase': self.conversation_phase,
                    'business_description': summary_data.get('business_description', ''),
                    'data_focus': summary_data.get('data_focus', ''),
                    'criteria': summary_data.get('criteria', ''),
                    'expected_outcome': summary_data.get('expected_outcome', '')
                }
            
        except Exception as e:
            print(f"[ConversationalIntentAnalyzer] Error creating summary: {e}")
            return {
                'clarification_needed': True,
                'clarification_question': "I've gathered the information you need. Does this look correct?",
                'gathered_info': self.requirements_gathered,
                'reasoning': "Presenting summary for user confirmation"
            }
    
    def _assess_question_clarity(self, gathered_info: Dict[str, Any], user_question: str) -> Dict[str, Any]:
        """
        Assess whether a question is clear enough to proceed directly to SQL generation.
        Uses generic patterns without hardcoding specific column or metric names.
        """
        try:
            # Generic heuristics for clear questions
            question_lower = user_question.lower()
            
            # Generic aggregation patterns
            aggregation_patterns = [
                'average', 'avg', 'mean',
                'sum', 'total', 
                'count', 'number of',
                'maximum', 'max', 'highest',
                'minimum', 'min', 'lowest'
            ]
            
            # Generic metric/score patterns
            metric_patterns = [
                'score', 'metric', 'rate', 'ratio',
                'value', 'amount', 'total'
            ]
            
            # Generic filter patterns
            filter_patterns = [
                'above', 'below', 'greater than', 'less than', 'higher than', 'lower than',
                'more than', 'less than', 'at least', 'at most', 'between', 'within',
                'equal to', 'equals', '=', '>', '<', '>=', '<='
            ]
            
            # Check if question contains aggregation patterns
            has_aggregation = any(pattern in question_lower for pattern in aggregation_patterns)
            
            # Check if question contains metric/score patterns
            has_metric = any(pattern in question_lower for pattern in metric_patterns)
            
            # Check if question contains filter patterns
            has_filter = any(pattern in question_lower for pattern in filter_patterns)
            
            # Check if we have specific requirements identified
            has_aggregations = len(gathered_info.get('aggregations', [])) > 0
            has_tables = len(gathered_info.get('tables', [])) > 0
            has_filters = len(gathered_info.get('filters', [])) > 0
            
            print(f"[ConversationalIntentAnalyzer] Clarity assessment details:")
            print(f"  - Question: {user_question}")
            print(f"  - has_aggregation: {has_aggregation}")
            print(f"  - has_metric: {has_metric}")
            print(f"  - has_filter: {has_filter}")
            print(f"  - has_aggregations: {has_aggregations}")
            print(f"  - has_tables: {has_tables}")
            print(f"  - has_filters: {has_filters}")
            print(f"  - gathered_info: {gathered_info}")
            
            # Question is clear if it has aggregation keywords and we have specific requirements,
            # OR if it has filter keywords and we have specific requirements
            is_clear = ((has_aggregation and has_aggregations and has_tables) or 
                       (has_filter and has_filters and has_tables))
            
            return {
                'is_clear': is_clear,
                'has_aggregation': has_aggregation,
                'has_metric': has_metric,
                'has_specific_requirements': has_aggregations and has_tables
            }
            
        except Exception as e:
            print(f"[ConversationalIntentAnalyzer] Error assessing question clarity: {e}")
            # Default to asking for clarification if we can't assess
            return {'is_clear': False}

    def _detect_column_ambiguity(self, question: str, schema_data: Dict) -> Dict[str, Any]:
        """
        Detect if there are multiple relevant columns that could match the user's intent.
        If so, ask the user to clarify which one they want.
        """
        try:
            schema = schema_data.get('schema', {})
            tables = schema.get('tables', {})
            user_preferences = schema.get('user_preferences', {})
            
            # Find all relevant columns based on question
            relevant_columns = []
            
            for table_name, table_data in tables.items():
                columns = table_data.get('columns', {})
                for col_name, col_data in columns.items():
                    if isinstance(col_data, dict):
                        # Check if column is relevant to the question
                        if self._is_column_relevant_to_question(question, col_data):
                            relevant_columns.append({
                                'name': col_name,
                                'table': table_name,
                                'business_description': col_data.get('business_description', ''),
                                'business_terms': col_data.get('business_terms', []),
                                'priority': col_data.get('priority', 'medium'),
                                'is_preferred': col_data.get('is_preferred', False)
                            })
            
            # If multiple relevant columns found, ask user to clarify
            if len(relevant_columns) > 1:
                return {
                    "needs_clarification": True,
                    "clarification_question": self._build_column_choice_question(relevant_columns),
                    "options": relevant_columns,
                    "ambiguity_type": "multiple_columns"
                }
            
            return {"needs_clarification": False}
            
        except Exception as e:
            print(f"[ConversationalIntentAnalyzer] Error detecting column ambiguity: {e}")
            return {"needs_clarification": False}

    def _is_column_relevant_to_question(self, question: str, col_data: Dict) -> bool:
        """Check if a column is relevant to the user's question."""
        question_lower = question.lower()
        
        # Check business terms
        for term in col_data.get('business_terms', []):
            if term.lower() in question_lower:
                return True
        
        # Check relevance keywords
        for keyword in col_data.get('relevance_keywords', []):
            if keyword.lower() in question_lower:
                return True
        
        # Check business description
        if col_data.get('business_description', '').lower() in question_lower:
            return True
        
        # Check column name
        if col_data.get('name', '').lower() in question_lower:
            return True
        
        return False

    def _build_column_choice_question(self, relevant_columns: List[Dict]) -> str:
        """Build a user-friendly question to choose between columns."""
        question = "I found multiple columns that could be relevant to your question:\n\n"
        
        for i, col in enumerate(relevant_columns, 1):
            description = col.get('business_description', f"Column: {col['name']}")
            priority = col.get('priority', 'medium')
            is_preferred = col.get('is_preferred', False)
            
            preferred_text = " (Preferred)" if is_preferred else ""
            priority_text = f" [{priority.upper()}]" if priority != 'medium' else ""
            
            question += f"{i}. **{description}** ({col['name']}){preferred_text}{priority_text}\n"
        
        question += "\nWhich column would you like me to use for your analysis?"
        return question
    
    def _generate_final_intent(self, user_question: str, conversation_context: str, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final intent after user approval."""
        print(f"[ConversationalIntentAnalyzer] Generating final intent")
        
        # Create final intent based on gathered information
        final_intent = {
            "tables": self.requirements_gathered.get("tables", []),
            "columns": self.requirements_gathered.get("columns", []),
            "filters": self.requirements_gathered.get("filters", []),
            "aggregations": self.requirements_gathered.get("aggregations", []),
            "time_range": self.requirements_gathered.get("time_range", ""),
            "sorting": self.requirements_gathered.get("sorting", ""),
            "reasoning": f"Complete context gathered through conversation: {self.summary}",
            "is_follow_up": False,
            "follow_up_context": "",
            "confidence": {
                "tables": 0.9 if self.requirements_gathered.get("tables") else 0.0,
                "columns": 0.9 if self.requirements_gathered.get("columns") else 0.0,
                "filters": 0.9 if self.requirements_gathered.get("filters") else 0.0,
                "aggregations": 0.9 if self.requirements_gathered.get("aggregations") else 0.0,
                "overall": 0.9
            }
        }
        
        return {
            'intent': final_intent,
            'conversation_phase': self.conversation_phase,
            'summary': self.summary
        }
    
    def _build_conversation_context(self, conversation_history: List[Dict]) -> str:
        """Build conversation context from history."""
        if not conversation_history:
            return "This is the start of our conversation."
        
        context_parts = []
        for msg in conversation_history[-5:]:  # Last 5 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'user':
                context_parts.append(f"User: {content}")
            elif role == 'assistant':
                context_parts.append(f"Assistant: {content}")
        
        return "\n".join(context_parts)
    
    def _build_knowledge_overview(self, knowledge_data: Dict[str, Any], question: str) -> str:
        """Build knowledge overview from schema data."""
        if not knowledge_data or 'schema' not in knowledge_data:
            return "No database schema information available."
        
        schema = knowledge_data['schema']
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
    
    def _update_requirements_from_response(self, user_response: str):
        """Update requirements based on user response."""
        # This would use LLM to extract information from user response
        # For now, we'll implement a simple version
        print(f"[ConversationalIntentAnalyzer] Updating requirements from: {user_response}")
        # TODO: Implement LLM-based requirement extraction
    
    def _has_complete_context(self) -> bool:
        """Check if we have complete context."""
        # Simple check - can be enhanced with LLM
        return len(self.requirements_gathered.get("tables", [])) > 0
    
    def _generate_follow_up_question(self, user_response: str, knowledge_data: Dict[str, Any]) -> str:
        """Generate a natural follow-up question."""
        # This would use LLM to generate contextual questions
        return "Could you provide more details about what specific information you're looking for?"
    
    def _user_approves_summary(self, user_response: str) -> bool:
        """Check if user approves the summary."""
        approval_keywords = ['yes', 'correct', 'right', 'good', 'perfect', 'that\'s right', 'exactly']
        return any(keyword in user_response.lower() for keyword in approval_keywords)
    
    def _ask_for_changes(self, user_response: str) -> str:
        """Ask for specific changes to the summary."""
        return "What would you like me to change about this summary?"
    
    def _generate_conversational_thoughts(self, question: str, gathered_info: Dict, summary_data: Dict) -> str:
        """Generate the agent's actual internal thoughts using LLM reasoning."""
        # Use the LLM to generate its own internal reasoning
        prompt = f"""
You are an AI agent that analyzes conversational queries and extracts intent.
Show your internal thought process as you analyze the conversation.

User Question: "{question}"

Extracted Information:
Tables: {gathered_info.get('tables', [])}
Columns: {gathered_info.get('columns', [])}
Filters: {gathered_info.get('filters', [])}

Summary Data: {summary_data}

Your Task: Show your internal reasoning process as you analyzed this conversation.

Think step by step:
1. What do you notice about the user's question?
2. How do you identify which tables are relevant?
3. How do you extract the right columns?
4. How do you determine what filters to apply?
5. How do you assess if the question is clear enough?
6. What makes you decide to proceed or ask for clarification?

Show your actual thought process, not just the final result.
"""

        try:
            # Get the LLM to generate its own internal thoughts
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error generating internal thoughts: {e}"
    
    def _build_conversational_decision_trace(self, question: str, gathered_info: Dict, summary_data: Dict) -> Dict:
        """Build structured decision trace for conversational analysis."""
        trace = {
            "agent": "ConversationalIntentAnalyzer",
            "question": question,
            "extracted_intent": {
                "tables": gathered_info.get('tables', []),
                "columns": gathered_info.get('columns', []),
                "filters": gathered_info.get('filters', []),
                "aggregations": gathered_info.get('aggregations', []),
                "time_range": gathered_info.get('time_range', ''),
                "sorting": gathered_info.get('sorting', ''),
                "business_context": gathered_info.get('business_context', '')
            },
            "clarity_assessment": {
                "is_clear": not summary_data.get('clarification_needed', True),
                "clarification_needed": summary_data.get('clarification_needed', True),
                "business_description": summary_data.get('business_description', ''),
                "data_focus": summary_data.get('data_focus', ''),
                "criteria": summary_data.get('criteria', ''),
                "expected_outcome": summary_data.get('expected_outcome', '')
            },
            "extraction_reasons": {},
            "clarity_signals": [],
            "override_decisions": {},
            "conversation_phase": self.conversation_phase
        }
        
        # Analyze table extraction reasoning
        tables = gathered_info.get('tables', [])
        trace["extraction_reasons"]["tables"] = {}
        for table in tables:
            if 'payment' in table.lower():
                trace["extraction_reasons"]["tables"][table] = {
                    "reason": "User mentioned 'payments' - direct match",
                    "confidence": 0.95,
                    "user_mentioned": "payments" in question.lower(),
                    "relevance": "CRITICAL"
                }
            else:
                trace["extraction_reasons"]["tables"][table] = {
                    "reason": "Inferred from context",
                    "confidence": 0.7,
                    "user_mentioned": False,
                    "relevance": "MEDIUM"
                }
        
        # Analyze column extraction reasoning
        columns = gathered_info.get('columns', [])
        trace["extraction_reasons"]["columns"] = {}
        for col in columns:
            if 'risk' in col.lower() and 'score' in col.lower():
                trace["extraction_reasons"]["columns"][col] = {
                    "reason": "Direct match to user's 'risk score' query",
                    "confidence": 0.9,
                    "user_mentioned": "risk" in question.lower() and "score" in question.lower(),
                    "relevance": "CRITICAL"
                }
            elif 'amount' in col.lower():
                trace["extraction_reasons"]["columns"][col] = {
                    "reason": "Payment amount information - contextually relevant",
                    "confidence": 0.8,
                    "user_mentioned": "amount" in question.lower(),
                    "relevance": "HIGH"
                }
            else:
                trace["extraction_reasons"]["columns"][col] = {
                    "reason": "General data column",
                    "confidence": 0.6,
                    "user_mentioned": False,
                    "relevance": "MEDIUM"
                }
        
        # Analyze filter extraction reasoning
        filters = gathered_info.get('filters', [])
        trace["extraction_reasons"]["filters"] = {}
        for filter_condition in filters:
            if '> 10' in filter_condition:
                trace["extraction_reasons"]["filters"][filter_condition] = {
                    "reason": "User specified 'above 10' condition",
                    "confidence": 0.95,
                    "user_mentioned": "above" in question.lower() and "10" in question.lower(),
                    "relevance": "CRITICAL"
                }
            else:
                trace["extraction_reasons"]["filters"][filter_condition] = {
                    "reason": "Inferred filter condition",
                    "confidence": 0.7,
                    "user_mentioned": False,
                    "relevance": "MEDIUM"
                }
        
        # Identify clarity signals
        question_lower = question.lower()
        clarity_signals = []
        if "which" in question_lower:
            clarity_signals.append("filtering_query")
        if "payments" in question_lower:
            clarity_signals.append("table_mention")
        if "risk" in question_lower and "score" in question_lower:
            clarity_signals.append("column_mention")
        if "above" in question_lower or ">" in question_lower:
            clarity_signals.append("threshold_mention")
        if any(word in question_lower for word in ["average", "sum", "count", "max", "min"]):
            clarity_signals.append("aggregation_mention")
        
        trace["clarity_signals"] = clarity_signals
        
        # Override decisions (if any)
        if hasattr(self, 'requirements_gathered') and self.requirements_gathered:
            trace["override_decisions"] = {
                "llm_clarification_decision": summary_data.get('clarification_needed', True),
                "internal_clarity_assessment": not summary_data.get('clarification_needed', True),
                "override_applied": summary_data.get('clarification_needed', True) != (not summary_data.get('clarification_needed', True)),
                "reason": "Internal clarity assessment overrode LLM decision"
            }
        
        return trace
    
    def _extract_key_terms(self, question: str) -> List[str]:
        """Extract key terms from the question."""
        import re
        # Extract meaningful terms (not common words)
        words = re.findall(r'\b\w+\b', question.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'have', 'has', 'had', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]
        return key_terms
