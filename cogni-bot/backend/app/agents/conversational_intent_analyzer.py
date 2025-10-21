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
            elif self.conversation_phase == "human_clarification":
                return self._handle_human_clarification_response(user_question, conversation_context, knowledge_data)
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
        
        # Check for column ambiguity before LLM analysis (only for very ambiguous cases)
        column_ambiguity = self._detect_column_ambiguity(user_question, knowledge_data)
        print(f"[ConversationalIntentAnalyzer] Column ambiguity check: needs_clarification={column_ambiguity.get('needs_clarification', False)}, options_count={len(column_ambiguity.get('options', []))}")
        
        if column_ambiguity.get('needs_clarification', False):
            # Ask for clarification if there are 2+ relevant columns (any ambiguity)
            if len(column_ambiguity.get('options', [])) >= 2:
                print(f"[ConversationalIntentAnalyzer] Column ambiguity detected with {len(column_ambiguity.get('options', []))} options, asking user to clarify")
                return {
                    'clarification_needed': True,
                    'clarification_question': column_ambiguity['clarification_question'],
                    'ambiguity_type': column_ambiguity['ambiguity_type'],
                    'options': column_ambiguity['options'],
                    'conversation_phase': 'clarification_needed'
                }
            else:
                print(f"[ConversationalIntentAnalyzer] Column ambiguity detected but only {len(column_ambiguity.get('options', []))} options, proceeding with intelligent selection")

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

INTELLIGENT BUSINESS ANALYSIS:
- For questions asking about "high" or "low" values, assume they mean above/below average
- For percentage questions, you can calculate percentages using COUNT and GROUP BY
- For comparison questions (vs, versus, by), use appropriate grouping columns
- For complex aggregations, include both the base columns and aggregation functions needed
- Don't ask for clarification on obvious business analysis questions

AGGREGATION REQUIREMENTS:
- When user asks for percentages, include: COUNT(*), GROUP BY, percentage calculation
- When user asks for "high" values, include: AVG() for threshold, WHERE > threshold
- When user asks for comparisons, include: GROUP BY comparison_column, COUNT(*)
- Always include the necessary columns for the analysis (e.g., IsManualPayment for manual vs automated)

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
            print(f"  - has_business_analysis: {question_clarity.get('has_business_analysis', False)}")
            print(f"  - has_specific_requirements: {question_clarity.get('has_specific_requirements', False)}")
            
            # Override LLM decision if our assessment says the question is clear
            if question_clarity.get('is_clear', False):
                print(f"[ConversationalIntentAnalyzer] Overriding LLM - question is actually clear")
                # Move to summarizing phase
                self.conversation_phase = "summarizing"
                return self._create_summary(gathered_info, user_question, knowledge_data)
            elif analysis.get("needs_clarification", False):
                # Use human-in-the-loop for better clarification
                print(f"[ConversationalIntentAnalyzer] Triggering human-in-the-loop clarification")
                return self._generate_human_in_loop_questions(user_question, gathered_info, knowledge_data)
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
                # Question needs clarification, use human-in-the-loop validation
                print(f"[ConversationalIntentAnalyzer] Question needs clarification, triggering human-in-the-loop validation")
                return self._generate_human_in_loop_questions(user_question, self.requirements_gathered, knowledge_data)
            
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
        Uses only schema metadata and gathered information, no hardcoded patterns.
        """
        try:
            # Check if we have specific requirements identified from schema
            has_aggregations = len(gathered_info.get('aggregations', [])) > 0
            has_tables = len(gathered_info.get('tables', [])) > 0
            has_filters = len(gathered_info.get('filters', [])) > 0
            has_columns = len(gathered_info.get('columns', [])) > 0
            
            print(f"[ConversationalIntentAnalyzer] Clarity assessment details:")
            print(f"  - Question: {user_question}")
            print(f"  - has_aggregations: {has_aggregations}")
            print(f"  - has_tables: {has_tables}")
            print(f"  - has_filters: {has_filters}")
            print(f"  - has_columns: {has_columns}")
            print(f"  - gathered_info: {gathered_info}")
            
            # Question is clear if we have specific requirements from schema
            is_clear = (has_tables and (has_columns or has_filters or has_aggregations))
            
            return {
                'is_clear': is_clear,
                'has_aggregations': has_aggregations,
                'has_tables': has_tables,
                'has_filters': has_filters,
                'has_columns': has_columns,
                'has_specific_requirements': has_aggregations or has_filters or has_tables or has_columns
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
            
            print(f"[ConversationalIntentAnalyzer] Found {len(relevant_columns)} relevant columns: {[col['name'] for col in relevant_columns]}")
            
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
        """Check if a column is relevant to the user's question using only schema metadata."""
        question_lower = question.lower()
        
        # Extract key terms from the question for better matching
        question_terms = set()
        for word in question_lower.split():
            if len(word) > 2:  # Skip short words
                question_terms.add(word)
        
        # Check business terms from schema metadata (exact match required)
        for term in col_data.get('business_terms', []):
            if term.lower() in question_lower:
                return True
        
        # Check relevance keywords from schema metadata (exact match required)
        for keyword in col_data.get('relevance_keywords', []):
            if keyword.lower() in question_lower:
                return True
        
        # Check business description from schema metadata (partial match for substantial descriptions)
        business_desc = col_data.get('business_description', '').lower()
        if business_desc and len(business_desc) > 10:
            # Check if any significant words from business description appear in question
            desc_words = set(word for word in business_desc.split() if len(word) > 3)
            if desc_words.intersection(question_terms):
                return True
        
        # Check column name (exact match)
        col_name = col_data.get('name', '').lower()
        if col_name and col_name in question_lower:
            return True
        
        # Check for semantic similarity in column names (split into meaningful parts)
        col_parts = col_name.replace('_', ' ').replace('-', ' ').split()
        for part in col_parts:
            if len(part) > 2 and part in question_lower:
                return True
        
        return False

    def _build_column_choice_question(self, relevant_columns: List[Dict]) -> str:
        """Build a user-friendly question to choose between columns."""
        question = "I found multiple columns that could be relevant to your question:\n\n"
        
        for i, col in enumerate(relevant_columns, 1):
            # Create business-friendly description
            col_name = col.get('name', '')
            business_desc = col.get('business_description', '')
            
            # If no business description, create one from column name
            if not business_desc:
                business_desc = self._create_business_description(col_name)
            
            priority = col.get('priority', 'medium')
            is_preferred = col.get('is_preferred', False)
            
            preferred_text = " (Recommended)" if is_preferred else ""
            priority_text = f" [{priority.upper()}]" if priority != 'medium' else ""
            
            question += f"{i}. **{business_desc}**{preferred_text}{priority_text}\n"
        
        question += "\nWhich column would you like me to use for your analysis?"
        question += "\n\nYou can respond with the number (1, 2, etc.) or describe which one you prefer."
        return question
    
    def _create_business_description(self, col_name: str) -> str:
        """Create a business-friendly description from column name using only schema metadata."""
        # Simply convert column name to readable format
        # No hardcoded patterns - let schema metadata handle the business context
        return f"{col_name.replace('_', ' ').title()}"
    
    def _handle_column_clarification_response(self, user_response: str, relevant_columns: List[Dict]) -> Dict[str, Any]:
        """Handle user response to column clarification."""
        try:
            user_response_lower = user_response.lower().strip()
            
            # Check if user selected a number
            if user_response_lower.isdigit():
                choice_index = int(user_response_lower) - 1
                if 0 <= choice_index < len(relevant_columns):
                    selected_column = relevant_columns[choice_index]
                    print(f"[ConversationalIntentAnalyzer] User selected column: {selected_column['name']}")
                    return {
                        'clarification_needed': False,
                        'selected_column': selected_column,
                        'conversation_phase': 'column_selected'
                    }
            
            # Check if user described their preference
            for i, col in enumerate(relevant_columns):
                col_name = col.get('name', '').lower()
                business_desc = col.get('business_description', '').lower()
                
                # Check if user response matches column name or description
                if (col_name in user_response_lower or 
                    any(word in user_response_lower for word in col_name.split('_')) or
                    any(word in user_response_lower for word in business_desc.split())):
                    print(f"[ConversationalIntentAnalyzer] User described preference for column: {col['name']}")
                    return {
                        'clarification_needed': False,
                        'selected_column': col,
                        'conversation_phase': 'column_selected'
                    }
            
            # If no clear match, ask for clarification
            return {
                'clarification_needed': True,
                'clarification_question': "I didn't understand your choice. Please select a number (1, 2, 3, etc.) or describe which column you prefer.",
                'options': relevant_columns,
                'conversation_phase': 'column_clarification'
            }
            
        except Exception as e:
            print(f"[ConversationalIntentAnalyzer] Error handling column clarification: {e}")
            return {
                'clarification_needed': True,
                'clarification_question': "I didn't understand your choice. Please select a number (1, 2, 3, etc.) or describe which column you prefer.",
                'options': relevant_columns,
                'conversation_phase': 'column_clarification'
            }
    
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
        
        # Add aggregation patterns if available and relevant to the question
        if 'aggregation_patterns' in schema and schema['aggregation_patterns']:
            question_lower = question.lower() if question else ""
            pattern_keywords = ['percentage', 'breakdown', 'vs', 'versus', 'comparison', 'group by', 'aggregation', 'analysis']
            
            if any(keyword in question_lower for keyword in pattern_keywords):
                overview_parts.append("\nAvailable Aggregation Patterns:")
                for pattern in schema['aggregation_patterns']:
                    if isinstance(pattern, dict):
                        pattern_name = pattern.get('name', 'Unknown Pattern')
                        pattern_keywords = pattern.get('keywords', [])
                        pattern_example = pattern.get('example_question', 'No example')
                        overview_parts.append(f"  - {pattern_name}: Keywords: {', '.join(pattern_keywords)} | Example: {pattern_example}")
        
        # Add AI preferences if available
        if 'ai_preferences' in schema and schema['ai_preferences']:
            overview_parts.append("\nAI Preferences:")
            for preference in schema['ai_preferences']:
                if isinstance(preference, dict):
                    preference_name = preference.get('name', 'Unknown Preference')
                    preference_value = preference.get('value', 'No value')
                    preference_description = preference.get('description', '')
                    overview_parts.append(f"  - {preference_name}: {preference_value}")
                    if preference_description:
                        overview_parts.append(f"    Description: {preference_description}")
        
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

    def _generate_human_in_loop_questions(self, user_question: str, gathered_info: Dict[str, Any], knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate dynamic human-in-the-loop questions for intent validation.
        Uses LLM to generate contextual questions based on the current understanding.
        """
        print(f"[ConversationalIntentAnalyzer] Generating human-in-the-loop questions")
        
        # Build knowledge overview for context
        knowledge_overview = self._build_knowledge_overview(knowledge_data, user_question)
        
        # Create a comprehensive prompt for generating clarification questions
        clarification_prompt = f"""You are an expert data analyst helping a user clarify their data needs. Based on the user's question and what you understand so far, generate 3-5 dynamic clarification questions that would help ensure you have complete context.

USER'S ORIGINAL QUESTION:
{user_question}

WHAT I UNDERSTAND SO FAR:
- Tables: {gathered_info.get('tables', [])}
- Columns: {gathered_info.get('columns', [])}
- Filters: {gathered_info.get('filters', [])}
- Aggregations: {gathered_info.get('aggregations', [])}
- Time Range: {gathered_info.get('time_range', 'Not specified')}
- Business Context: {gathered_info.get('business_context', 'Not specified')}

AVAILABLE DATABASE SCHEMA:
{knowledge_overview}

Generate 3-5 clarification questions that would help ensure complete understanding. The questions should be:
1. Natural and conversational
2. Specific to the user's question
3. Help identify any missing information
4. Cover potential ambiguities
5. Be actionable (user can answer them)

Also provide a confidence assessment of your current understanding.

Respond in this JSON format:
{{
    "confidence_level": 0.0-1.0,
    "understanding_complete": true/false,
    "clarification_questions": [
        {{
            "id": "q1",
            "question": "Natural question text",
            "purpose": "What this question helps clarify",
            "required": true/false
        }},
        {{
            "id": "q2", 
            "question": "Another natural question",
            "purpose": "What this clarifies",
            "required": false
        }}
    ],
    "summary": "Brief summary of what you understand and what's still unclear",
    "recommendations": [
        "What you recommend asking about",
        "Potential issues to clarify"
    ]
}}"""

        try:
            # Use LLM to generate dynamic questions
            messages = [
                SystemMessage(content="You are an expert data analyst who helps users clarify their data needs through natural conversation."),
                HumanMessage(content=clarification_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse the JSON response
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                clarification_data = json.loads(json_match.group())
            else:
                # Fallback if JSON parsing fails
                clarification_data = {
                    "confidence_level": 0.5,
                    "understanding_complete": False,
                    "clarification_questions": [
                        {
                            "id": "q1",
                            "question": "Could you clarify what specific information you're looking for?",
                            "purpose": "General clarification",
                            "required": True
                        }
                    ],
                    "summary": "Need more information to proceed",
                    "recommendations": ["Please provide more details about your requirements"]
                }
            
            print(f"[ConversationalIntentAnalyzer] Generated {len(clarification_data.get('clarification_questions', []))} clarification questions")
            print(f"[ConversationalIntentAnalyzer] Confidence level: {clarification_data.get('confidence_level', 0.0)}")
            
            return {
                'needs_human_clarification': True,
                'human_in_loop_questions': clarification_data,
                'conversation_phase': 'human_clarification'
            }
            
        except Exception as e:
            print(f"[ConversationalIntentAnalyzer] Error generating human-in-loop questions: {e}")
            # Fallback to simple clarification
            return {
                'needs_human_clarification': True,
                'human_in_loop_questions': {
                    "confidence_level": 0.3,
                    "understanding_complete": False,
                    "clarification_questions": [
                        {
                            "id": "q1",
                            "question": "Could you please clarify what specific information you're looking for?",
                            "purpose": "General clarification",
                            "required": True
                        }
                    ],
                    "summary": "Need more information to proceed",
                    "recommendations": ["Please provide more details"]
                },
                'conversation_phase': 'human_clarification'
            }

    def _handle_human_clarification_response(self, user_response: str, conversation_context: str, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle user's response to human-in-the-loop clarification questions.
        """
        print(f"[ConversationalIntentAnalyzer] Handling human clarification response")
        
        # Use LLM to analyze the user's response and update understanding
        analysis_prompt = f"""You are an expert data analyst. The user has responded to your clarification questions. Analyze their response and update your understanding of their data needs.

CONVERSATION CONTEXT:
{conversation_context}

USER'S RESPONSE TO CLARIFICATION:
{user_response}

CURRENT UNDERSTANDING:
{self.requirements_gathered}

Analyze the user's response and determine:
1. What new information did they provide?
2. Is your understanding now complete?
3. Do you need any additional clarification?
4. Can you proceed with SQL generation?

Respond in this JSON format:
{{
    "understanding_updated": true/false,
    "new_information": {{
        "tables": ["any new tables mentioned"],
        "columns": ["any new columns mentioned"],
        "filters": ["any new filters mentioned"],
        "aggregations": ["any new aggregations mentioned"],
        "time_range": "any time range mentioned",
        "business_context": "any business context mentioned"
    }},
    "understanding_complete": true/false,
    "confidence_level": 0.0-1.0,
    "can_proceed": true/false,
    "still_unclear": ["what's still unclear"],
    "next_steps": "what should happen next"
}}"""

        try:
            messages = [
                SystemMessage(content="You are an expert data analyst who helps users clarify their data needs."),
                HumanMessage(content=analysis_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {
                    "understanding_updated": False,
                    "new_information": {},
                    "understanding_complete": False,
                    "confidence_level": 0.3,
                    "can_proceed": False,
                    "still_unclear": ["Need more clarification"],
                    "next_steps": "Ask for more details"
                }
            
            # Update gathered requirements if new information was provided
            if analysis.get("understanding_updated", False):
                new_info = analysis.get("new_information", {})
                for key, value in new_info.items():
                    if value and key in self.requirements_gathered:
                        if isinstance(self.requirements_gathered[key], list):
                            self.requirements_gathered[key].extend(value)
                        else:
                            self.requirements_gathered[key] = value
            
            print(f"[ConversationalIntentAnalyzer] Understanding updated: {analysis.get('understanding_updated', False)}")
            print(f"[ConversationalIntentAnalyzer] Can proceed: {analysis.get('can_proceed', False)}")
            
            if analysis.get("can_proceed", False):
                # Move to summarizing phase
                self.conversation_phase = "summarizing"
                return self._create_summary(self.requirements_gathered, user_response, knowledge_data)
            else:
                # Need more clarification
                return self._generate_human_in_loop_questions(user_response, self.requirements_gathered, knowledge_data)
                
        except Exception as e:
            print(f"[ConversationalIntentAnalyzer] Error handling human clarification: {e}")
            return {
                'needs_human_clarification': True,
                'clarification_question': "I need more information to help you. Could you please provide more details about what you're looking for?",
                'conversation_phase': 'human_clarification'
            }
    
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
