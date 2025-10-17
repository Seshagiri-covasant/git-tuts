import json
import re
from typing import Any, Dict, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseLanguageModel


class ConversationalContextClipper:
    """
    A conversational AI agent that intelligently clips relevant database context
    for the LLM, just like ChatGPT understands what information is relevant.
    """
    
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method that uses conversational AI to clip relevant context.
        Uses pure LLM-based understanding without hardcoded patterns.
        """
        try:
            # Get the current user question and conversation context
            user_question = state.get('user_question', '')
            conversation_history = state.get('conversation_history', [])
            knowledge_data = state.get('knowledge_data', {})
            intent = state.get('intent', {})
            
            print(f"[ConversationalContextClipper] Processing: {user_question}")
            print(f"[ConversationalContextClipper] Knowledge data: {len(knowledge_data)} items")
            
            # Build conversation context for the LLM
            conversation_context = self._build_conversation_context(conversation_history)
            
            # Use LLM to determine what context is relevant
            relevant_context = self._analyze_relevant_context(
                user_question, conversation_context, knowledge_data, intent
            )
            
            print(f"[ConversationalContextClipper] Relevant context: {len(relevant_context)} items")
            
            # CRITICAL FIX: Add CLIPPED message for query generator
            import json as _json
            clipped_message = f"CLIPPED:{_json.dumps(relevant_context)}"
            
            # Add clipped message to messages for query generator to find
            if 'messages' not in state:
                state['messages'] = []
            state['messages'].append({
                'role': 'system',
                'content': clipped_message
            })
            
            return {
                **state,
                'clipped_context': relevant_context,
                'conversation_context': conversation_context,
                'clipped_message': clipped_message
            }
            
        except Exception as e:
            print(f"[ConversationalContextClipper] Error: {e}")
            return {
                **state,
                'clipped_context': {},
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
    
    def _analyze_relevant_context(self, user_question: str, conversation_context: str, knowledge_data: Dict, intent: Dict) -> Dict:
        """
        Use LLM to determine what database context is relevant for the user's question.
        This is the core of the conversational AI approach.
        """
        
        # Create a comprehensive prompt for the LLM to understand what context is relevant
        system_prompt = """You are a conversational AI assistant that helps users with database queries.
        
Your role is to:
1. Understand what database information is relevant to the user's question
2. Select the most important tables and columns from the available schema
3. Consider the conversation context to understand what the user needs
4. Be natural and conversational in your analysis

Guidelines:
- Understand the user's question in the context of our conversation
- Select only the most relevant database information
- Consider if this is a follow-up to a previous question
- Be helpful and conversational, not robotic
- Focus on what's truly needed to answer the question

Remember: You should understand context naturally, just like ChatGPT does."""
        
        # Build knowledge overview for the LLM
        knowledge_overview = self._build_knowledge_overview(knowledge_data, user_question)
        
        user_prompt = f"""Conversation Context:
{conversation_context}

Current User Question: {user_question}

Current Intent Analysis: {intent}

Available Database Schema:
{knowledge_overview}

Please analyze this question and determine what database context is most relevant:
1. What tables are most important for answering this question?
2. What columns are most relevant from those tables?
3. What additional context might be helpful?
4. How does this relate to our previous conversation?

Respond in this JSON format:
{{
    "relevant_tables": ["table1", "table2"],
    "relevant_columns": ["column1", "column2"],
    "additional_context": ["context1", "context2"],
    "reasoning": "Why you selected this context",
    "is_follow_up": true/false,
    "follow_up_context": "How this relates to previous conversation"
}}"""

        try:
            # Use the LLM to analyze what context is relevant
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Parse the LLM response
            try:
                context_analysis = json.loads(response_text)
                return context_analysis
                
            except json.JSONDecodeError:
                print(f"[ConversationalContextClipper] Failed to parse LLM response: {response_text}")
                # Fallback: return basic context structure
                return {
                    "relevant_tables": [],
                    "relevant_columns": [],
                    "additional_context": [],
                    "reasoning": "Failed to parse LLM response",
                    "is_follow_up": False,
                    "follow_up_context": ""
                }
                
        except Exception as e:
            print(f"[ConversationalContextClipper] Error in LLM analysis: {e}")
            # Fallback: return basic context structure
            return {
                "relevant_tables": [],
                "relevant_columns": [],
                "additional_context": [],
                "reasoning": f"Error: {e}",
                "is_follow_up": False,
                "follow_up_context": ""
            }
    
    def _build_knowledge_overview(self, knowledge_data: Dict[str, Any], question: str) -> str:
        """
        Build a natural overview of the database schema for the LLM.
        This helps the LLM understand what's available without hardcoded patterns.
        """
        if not knowledge_data:
            return "No database schema information available."
        
        # Extract simple keywords from the question for relevance
        keywords = set(re.findall(r"[a-zA-Z0-9_]{3,}", (question or "").lower()))
        
        # Build natural schema overview
        tables = []
        columns = []
        synonyms = []
        
        for key, value in knowledge_data.items():
            if key.startswith("table:"):
                table_name = key.split(":", 1)[1]
                tables.append(table_name)
            elif key.startswith("column:"):
                column_name = key.split(":", 1)[1]
                columns.append(column_name)
            elif key.startswith("synonym:") and isinstance(value, list):
                synonym_text = f"{key.replace('synonym:', '')} -> {', '.join(value)}"
                synonyms.append(synonym_text)
        
        # Sort by relevance to the question
        def score_relevance(name: str) -> int:
            name_lower = name.lower()
            return sum(1 for kw in keywords if kw in name_lower)
        
        tables_sorted = sorted(tables, key=lambda n: (-score_relevance(n), n))
        columns_sorted = sorted(columns, key=lambda n: (-score_relevance(n), n))
        
        # Build natural overview
        overview_parts = []
        
        if tables_sorted:
            overview_parts.append(f"Available Tables: {', '.join(tables_sorted[:20])}")
        
        if columns_sorted:
            overview_parts.append(f"Available Columns: {', '.join(columns_sorted[:50])}")
        
        if synonyms:
            overview_parts.append(f"Synonyms: {', '.join(synonyms[:20])}")
        
        return "\n".join(overview_parts) if overview_parts else "No schema information available."
    
    def _infer_context_from_conversation(self, user_question: str, conversation_context: str) -> Dict:
        """
        Use LLM to infer relevant context from conversation when no explicit schema is available.
        This handles cases where the user is asking follow-up questions.
        """
        
        system_prompt = """You are a conversational AI that helps users with database queries.
        
Your role is to:
1. Understand what database information is relevant based on our conversation
2. Infer what context the user needs
3. Consider the context of our previous discussion
4. Be natural and conversational in your analysis

Guidelines:
- Understand the user's question in context
- Infer what database information they need
- Consider if this is a follow-up to a previous question
- Be helpful and conversational, not robotic"""
        
        user_prompt = f"""Conversation Context:
{conversation_context}

Current User Question: {user_question}

Please analyze this question and infer what database context is relevant:
1. What kind of information are they looking for?
2. What database tables might be relevant?
3. What columns might they need?
4. What additional context might be helpful?

Respond in this JSON format:
{{
    "relevant_tables": ["inferred_table1", "inferred_table2"],
    "relevant_columns": ["inferred_column1", "inferred_column2"],
    "additional_context": ["inferred_context1", "inferred_context2"],
    "reasoning": "Why you inferred this context",
    "is_follow_up": true/false,
    "follow_up_context": "How this relates to previous conversation"
}}"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            try:
                context_analysis = json.loads(response_text)
                return context_analysis
                
            except json.JSONDecodeError:
                print(f"[ConversationalContextClipper] Failed to parse conversation inference: {response_text}")
                return {
                    "relevant_tables": [],
                    "relevant_columns": [],
                    "additional_context": [],
                    "reasoning": "Failed to parse conversation inference",
                    "is_follow_up": True,
                    "follow_up_context": "Inferred from conversation context"
                }
                
        except Exception as e:
            print(f"[ConversationalContextClipper] Error in conversation inference: {e}")
            return {
                "relevant_tables": [],
                "relevant_columns": [],
                "additional_context": [],
                "reasoning": f"Error: {e}",
                "is_follow_up": True,
                "follow_up_context": "Error in conversation inference"
            }