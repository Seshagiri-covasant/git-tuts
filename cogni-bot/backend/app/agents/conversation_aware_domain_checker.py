"""
Conversation-Aware Domain Checker

This agent checks domain relevance with conversation context awareness.
"""

import json
from typing import Dict, List, Any, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.repositories.chatbot_db_util import ChatbotDbUtil


class ConversationAwareDomainChecker:
    """
    Domain checker that considers conversation context for better relevance detection.
    """
    
    def __init__(self, llm: BaseLanguageModel, chatbot_db_util: ChatbotDbUtil = None):
        self.llm = llm
        self.chatbot_db_util = chatbot_db_util
    
    def check_domain_relevance_with_context(self, question: str, conversation_history: List[Dict], 
                                          semantic_schema: Dict, chatbot_id: str) -> Dict[str, Any]:
        """
        Check domain relevance considering conversation context.
        
        Args:
            question: Current user question
            conversation_history: Previous conversation messages
            semantic_schema: Database schema information
            chatbot_id: Chatbot identifier
            
        Returns:
            Dictionary with relevance information
        """
        try:
            # Build conversation context
            context = self._build_conversation_context(conversation_history)
            
            # Create prompt for domain relevance check
            prompt = self._create_relevance_prompt(question, context, semantic_schema)
            
            # Use LLM to determine relevance
            response = self.llm.invoke([
                SystemMessage(content="You are a domain relevance checker. Analyze if the question is relevant to the database domain."),
                HumanMessage(content=prompt)
            ])
            
            # Parse LLM response
            try:
                result = json.loads(response.content)
                return result
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return self._fallback_relevance_check(question, semantic_schema)
                
        except Exception as e:
            print(f"[ConversationAwareDomainChecker] Error: {e}")
            return self._fallback_relevance_check(question, semantic_schema)
    
    def _build_conversation_context(self, conversation_history: List[Dict]) -> str:
        """Build conversation context string."""
        if not conversation_history:
            return "No previous conversation."
        
        context_parts = []
        for msg in conversation_history[-5:]:  # Last 5 messages
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def _create_relevance_prompt(self, question: str, context: str, semantic_schema: Dict) -> str:
        """Create prompt for domain relevance checking."""
        schema_info = json.dumps(semantic_schema, indent=2)
        
        prompt = f"""
Analyze if this question is relevant to the database domain:

Current Question: {question}

Conversation Context:
{context}

Database Schema:
{schema_info}

A question is considered RELEVANT if it:
1. Asks about data in the available tables.
2. Contains query-related keywords (which, what, how many, show, find, get, list, etc.)
3. Mentions column names, table names, or data-related terms
4. Asks for aggregations, filters, or analysis of the data
5. Requests information that could be answered by querying the database

Examples of RELEVANT questions:
- "Which payments have a risk score above 10?" (mentions payments, risk score, filtering)
- "Show me all records" (general data request)
- "What is the average amount?" (aggregation request)
- "How many payments are there?" (counting request)

Examples of IRRELEVANT questions:
- "What is the weather today?" (not about database data)
- "How do I cook pasta?" (not about database data)
- "What time is it?" (not about database data)

Respond with JSON:
{{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Explanation of relevance decision",
    "is_follow_up": true/false,
    "follow_up_type": "clarification/refinement/continuation",
    "original_question": "Original question if follow-up"
}}
"""
        return prompt
    
    def _fallback_relevance_check(self, question: str, semantic_schema: Dict) -> Dict[str, Any]:
        """Fallback relevance check when LLM fails."""
        question_lower = question.lower()
        
        # Check if question mentions any table names from the schema
        tables = semantic_schema.get('tables', {})
        if isinstance(tables, dict):
            table_names = list(tables.keys())
        elif isinstance(tables, list):
            table_names = tables
        else:
            table_names = []
        
        # Check if question mentions any table names
        mentions_table = any(table_name.lower() in question_lower for table_name in table_names)
        
        # Check for common database query keywords
        query_keywords = ['select', 'from', 'where', 'show', 'find', 'get', 'list', 'which', 'what', 'how many', 'count', 'sum', 'average', 'max', 'min']
        has_query_keywords = any(keyword in question_lower for keyword in query_keywords)
        
        # Check for data-related terms
        data_terms = ['data', 'record', 'row', 'table', 'database', 'query', 'search', 'filter', 'sort', 'group']
        has_data_terms = any(term in question_lower for term in data_terms)
        
        # Check for column-related terms (risk score, payment, etc.)
        column_terms = ['score', 'risk', 'payment', 'amount', 'date', 'name', 'id', 'number', 'code']
        has_column_terms = any(term in question_lower for term in column_terms)
        
        # Determine relevance
        is_relevant = mentions_table or (has_query_keywords and (has_data_terms or has_column_terms))
        
        return {
            "is_relevant": is_relevant,
            "confidence": 0.8 if is_relevant else 0.2,
            "reasoning": f"Fallback check: mentions_table={mentions_table}, has_query_keywords={has_query_keywords}, has_data_terms={has_data_terms}, has_column_terms={has_column_terms}",
            "is_follow_up": False,
            "follow_up_type": None,
            "original_question": None
        }
