import json
import re
from typing import Optional, List, Dict, Set, Any
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseLanguageModel
from app.repositories.chatbot_db_util import ChatbotDbUtil


class ConversationalClarificationAgent:
    """
    A conversational AI agent that understands context naturally and asks for clarification
    only when truly needed, just like ChatGPT.
    """
    
    def __init__(self, llm: BaseLanguageModel, chatbot_db_util: ChatbotDbUtil = None):
        self.llm = llm
        self.chatbot_db_util = chatbot_db_util
        self.conversation_context = []
        
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method that handles conversational clarification.
        Uses pure LLM-based understanding without hardcoded patterns.
        """
        try:
            # Get the current user question
            user_question = state.get('user_question', '')
            conversation_history = state.get('conversation_history', [])
            intent = state.get('intent', {})
            
            print(f"[ConversationalClarification] Processing: {user_question}")
            print(f"[ConversationalClarification] Conversation history: {len(conversation_history)} messages")
            
            # Check if ConversationalIntentAnalyzer already determined clarification is needed
            if state.get('clarification_needed', False):
                print(f"[ConversationalClarification] ConversationalIntentAnalyzer already determined clarification needed")
                return {
                    **state,
                    'clarification_needed': True,
                    'clarification_question': state.get('clarification_question', 'Could you provide more details?'),
                    'conversation_context': self._build_conversation_context(conversation_history)
                }
            
            # Build conversation context for the LLM
            conversation_context = self._build_conversation_context(conversation_history)
            
            # Use LLM to understand if clarification is needed
            clarification_needed, clarification_question = self._analyze_conversation_context(
                user_question, conversation_context, intent
            )
            
            if clarification_needed:
                print(f"[ConversationalClarification] Asking for clarification: {clarification_question}")
                return {
                    **state,
                    'clarification_needed': True,
                    'clarification_question': clarification_question,
                    'conversation_context': conversation_context
                }
            else:
                print(f"[ConversationalClarification] No clarification needed, proceeding with intent")
                return {
                    **state,
                    'clarification_needed': False,
                    'conversation_context': conversation_context
                }
                
        except Exception as e:
            print(f"[ConversationalClarification] Error: {e}")
            return {
                **state,
                'clarification_needed': False,
                'error': str(e)
            }
    
    def _build_conversation_context(self, conversation_history: List[Dict]) -> str:
        """
        Build a natural conversation context from the history.
        This is like how ChatGPT remembers the conversation.
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
    
    def _analyze_conversation_context(self, user_question: str, conversation_context: str, intent: Dict) -> tuple[bool, str]:
        """
        Use LLM to analyze if clarification is needed based on conversation context.
        This is the core of the conversational AI approach.
        """
        
        # Create a comprehensive prompt for the LLM to understand the conversation
        system_prompt = """You are a conversational AI assistant that helps users with database queries. 
        
Your role is to:
1. Understand the user's question in the context of our conversation
2. Determine if you need clarification to help them effectively
3. Ask for clarification only when truly necessary
4. Flow naturally like a human conversation

Guidelines:
- If the user's question is clear and you have enough context, proceed without asking
- If the question is ambiguous or you need more information, ask a natural clarifying question
- Consider the conversation history to understand follow-up questions
- Be helpful and conversational, not robotic
- Only ask for clarification when you genuinely need it to help the user

Remember: You should understand context naturally, just like ChatGPT does."""

        user_prompt = f"""Conversation Context:
{conversation_context}

Current User Question: {user_question}

Current Intent Analysis: {json.dumps(intent, indent=2)}

Please analyze this conversation and determine:
1. Is the user's question clear enough to proceed?
2. Do you need clarification to help them effectively?
3. If clarification is needed, what should you ask?

Respond in this JSON format:
{{
    "needs_clarification": true/false,
    "clarification_question": "Your natural clarifying question here (if needed)",
    "reasoning": "Why you need clarification or why you don't"
}}"""

        try:
            # Use the LLM to analyze the conversation context
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Parse the LLM response
            try:
                analysis = json.loads(response_text)
                needs_clarification = analysis.get('needs_clarification', False)
                clarification_question = analysis.get('clarification_question', '')
                reasoning = analysis.get('reasoning', '')
                
                print(f"[ConversationalClarification] LLM Analysis: {reasoning}")
                
                return needs_clarification, clarification_question
                
            except json.JSONDecodeError:
                print(f"[ConversationalClarification] Failed to parse LLM response: {response_text}")
                # Fallback: if we can't parse, assume no clarification needed
                return False, ""
                
        except Exception as e:
            print(f"[ConversationalClarification] Error in LLM analysis: {e}")
            # Fallback: if LLM fails, assume no clarification needed
            return False, ""
    
    def process_clarification_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the user's response to a clarification question.
        This handles the natural flow of conversation.
        """
        try:
            user_response = state.get('user_question', '')
            original_intent = state.get('intent', {})
            
            print(f"[ConversationalClarification] Processing clarification response: {user_response}")
            
            # Use LLM to understand how the user's response relates to the original intent
            clarification_analysis = self._analyze_clarification_response(
                user_response, original_intent
            )
            
            if clarification_analysis['success']:
                # Update the intent with the clarification
                updated_intent = clarification_analysis['updated_intent']
                print(f"[ConversationalClarification] Updated intent: {updated_intent}")
                
                return {
                    **state,
                    'intent': updated_intent,
                    'clarification_needed': False,
                    'clarification_processed': True
                }
            else:
                # If we still don't understand, ask for more clarification
                return {
                    **state,
                    'clarification_needed': True,
                    'clarification_question': clarification_analysis['follow_up_question']
                }
            
        except Exception as e:
            print(f"[ConversationalClarification] Error processing clarification: {e}")
            return {
                **state,
                'clarification_needed': False,
                'error': str(e)
            }
    
    def _analyze_clarification_response(self, user_response: str, original_intent: Dict) -> Dict:
        """
        Use LLM to understand how the user's clarification response relates to the original intent.
        """
        
        system_prompt = """You are a conversational AI that helps users with database queries.
        
Your role is to:
1. Understand how the user's response clarifies their original question
2. Update the intent with the new information
3. Determine if you have enough information to proceed
4. Ask for more clarification only if truly needed

Be natural and conversational in your analysis."""

        user_prompt = f"""Original Intent: {json.dumps(original_intent, indent=2)}

User's Clarification Response: {user_response}

Please analyze how the user's response clarifies their original question and update the intent accordingly.

Respond in this JSON format:
{{
    "success": true/false,
    "updated_intent": {{
        "tables": ["table1", "table2"],
        "columns": ["column1", "column2"],
        "filters": ["filter1", "filter2"],
        "aggregations": ["agg1", "agg2"],
        "time_range": "time_range_info",
        "sorting": "sorting_info"
    }},
    "follow_up_question": "If you need more clarification, what should you ask?",
    "reasoning": "Why this analysis makes sense"
}}"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            try:
                analysis = json.loads(response_text)
                return analysis
                
            except json.JSONDecodeError:
                print(f"[ConversationalClarification] Failed to parse clarification analysis: {response_text}")
                return {
                    'success': False,
                    'updated_intent': original_intent,
                    'follow_up_question': "I didn't quite understand that. Could you please clarify?",
                    'reasoning': 'Failed to parse LLM response'
                }
                
        except Exception as e:
            print(f"[ConversationalClarification] Error in clarification analysis: {e}")
            return {
                'success': False,
                'updated_intent': original_intent,
                'follow_up_question': "I'm having trouble understanding. Could you please clarify?",
                'reasoning': f'Error: {e}'
            }