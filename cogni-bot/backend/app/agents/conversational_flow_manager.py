import logging
import json
from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from ..utils.exceptions import QueryGenerationException
from ..repositories.chatbot_db_util import ChatbotDbUtil
# from .enhanced_conversational_intent_analyzer import EnhancedConversationalIntentAnalyzer  # Deleted agent


class ConversationalFlowManager:
    """
    Manages the complete conversational flow for natural language to SQL conversion.
    Orchestrates the dialogue between user and AI, handling clarification, confirmation,
    and execution phases with human-like conversation patterns.
    """
    
    def __init__(self, llm, chatbot_db_util: ChatbotDbUtil = None, chatbot_id: str = None):
        self.llm = llm
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id
        self.logger = logging.getLogger(__name__)
        
        # Initialize the enhanced intent analyzer
        self.intent_analyzer = EnhancedConversationalIntentAnalyzer(
            llm=llm,
            chatbot_db_util=chatbot_db_util,
            chatbot_id=chatbot_id
        )
        
        # Conversation flow states
        self.FLOW_STATES = {
            "INITIAL": "initial",
            "CLARIFYING": "clarifying",
            "CONFIRMING": "confirming", 
            "EXECUTING": "executing",
            "COMPLETED": "completed"
        }
        
        # Conversation memory for maintaining context
        self.conversation_memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="conversation_history",
            input_key="user_input",
            output_key="ai_response"
        )

    def process_conversational_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for processing conversational queries.
        Handles the complete flow from initial query to final execution.
        
        Args:
            state: Current conversation state containing:
                - user_question: Current user query
                - conversation_history: Previous conversation messages
                - knowledge_data: Database schema and context
                - flow_state: Current flow state
                
        Returns:
            Updated state with conversational response and next steps
        """
        try:
            user_question = state.get("user_question", "")
            conversation_history = state.get("conversation_history", [])
            knowledge_data = state.get("knowledge_data", {})
            current_flow_state = state.get("flow_state", self.FLOW_STATES["INITIAL"])
            
            # Load conversation memory
            self._load_conversation_memory(conversation_history)
            
            # Route based on flow state
            if current_flow_state == self.FLOW_STATES["INITIAL"]:
                return self._handle_initial_query(state, user_question, knowledge_data)
            elif current_flow_state == self.FLOW_STATES["CLARIFYING"]:
                return self._handle_clarification_flow(state, user_question, knowledge_data)
            elif current_flow_state == self.FLOW_STATES["CONFIRMING"]:
                return self._handle_confirmation_flow(state, user_question, knowledge_data)
            elif current_flow_state == self.FLOW_STATES["EXECUTING"]:
                return self._handle_execution_flow(state, user_question, knowledge_data)
            else:
                return self._handle_completed_flow(state, user_question, knowledge_data)
                
        except Exception as e:
            self.logger.error(f"Error in conversational flow: {str(e)}")
            raise QueryGenerationException(f"Conversational flow failed: {str(e)}")

    def _handle_initial_query(self, state: Dict[str, Any], user_question: str, knowledge_data: Dict) -> Dict[str, Any]:
        """Handle the initial user query and determine the conversation path."""
        
        # Use the enhanced intent analyzer for initial analysis
        intent_state = {
            "user_question": user_question,
            "conversation_history": state.get("conversation_history", []),
            "knowledge_data": knowledge_data,
            "conversation_phase": "initial_analysis"
        }
        
        intent_result = self.intent_analyzer.analyze_intent_conversationally(intent_state)
        
        # Update the main state with intent analysis results
        state.update({
            "intent_analysis": intent_result.get("intent_analysis", {}),
            "clarification_needed": intent_result.get("clarification_needed", False),
            "clarification_questions": intent_result.get("clarification_questions", []),
            "conversation_phase": intent_result.get("conversation_phase", "initial_analysis"),
            "messages": intent_result.get("messages", [])
        })
        
        # Determine next flow state
        if intent_result.get("clarification_needed", False):
            state["flow_state"] = self.FLOW_STATES["CLARIFYING"]
        else:
            state["flow_state"] = self.FLOW_STATES["CONFIRMING"]
        
        return state

    def _handle_clarification_flow(self, state: Dict[str, Any], user_response: str, knowledge_data: Dict) -> Dict[str, Any]:
        """Handle the clarification conversation flow."""
        
        # Process the clarification response
        clarification_state = {
            "user_question": user_response,
            "conversation_history": state.get("conversation_history", []),
            "knowledge_data": knowledge_data,
            "conversation_phase": "clarification",
            "intent_analysis": state.get("intent_analysis", {}),
            "clarification_type": state.get("clarification_type", "general")
        }
        
        clarification_result = self.intent_analyzer.analyze_intent_conversationally(clarification_state)
        
        # Update state with clarification results
        state.update({
            "intent_analysis": clarification_result.get("intent_analysis", state.get("intent_analysis", {})),
            "clarification_needed": clarification_result.get("clarification_needed", False),
            "clarification_questions": clarification_result.get("clarification_questions", []),
            "conversation_phase": clarification_result.get("conversation_phase", "clarification"),
            "messages": clarification_result.get("messages", [])
        })
        
        # Determine next flow state
        if clarification_result.get("clarification_needed", False):
            # Continue clarification
            state["flow_state"] = self.FLOW_STATES["CLARIFYING"]
        else:
            # Move to confirmation
            state["flow_state"] = self.FLOW_STATES["CONFIRMING"]
            state["intent_summary"] = clarification_result.get("intent_summary", {})
        
        return state

    def _handle_confirmation_flow(self, state: Dict[str, Any], user_response: str, knowledge_data: Dict) -> Dict[str, Any]:
        """Handle the confirmation conversation flow."""
        
        # Process the confirmation response
        confirmation_state = {
            "user_question": user_response,
            "conversation_history": state.get("conversation_history", []),
            "knowledge_data": knowledge_data,
            "conversation_phase": "confirmation",
            "intent_analysis": state.get("intent_analysis", {}),
            "intent_summary": state.get("intent_summary", {})
        }
        
        confirmation_result = self.intent_analyzer.analyze_intent_conversationally(confirmation_state)
        
        # Update state with confirmation results
        state.update({
            "intent_analysis": confirmation_result.get("intent_analysis", state.get("intent_analysis", {})),
            "conversation_phase": confirmation_result.get("conversation_phase", "confirmation"),
            "messages": confirmation_result.get("messages", [])
        })
        
        # Determine next flow state based on user response
        if confirmation_result.get("ready_to_execute", False):
            state["flow_state"] = self.FLOW_STATES["EXECUTING"]
            state["final_intent"] = confirmation_result.get("final_intent", {})
        elif confirmation_result.get("clarification_needed", False):
            # User wants modifications, go back to clarification
            state["flow_state"] = self.FLOW_STATES["CLARIFYING"]
            state["clarification_questions"] = confirmation_result.get("clarification_questions", [])
        else:
            # Continue confirmation or handle additional context
            state["flow_state"] = self.FLOW_STATES["CONFIRMING"]
        
        return state

    def _handle_execution_flow(self, state: Dict[str, Any], user_question: str, knowledge_data: Dict) -> Dict[str, Any]:
        """Handle the execution flow - generate and execute SQL."""
        
        # Generate final SQL query
        final_sql = self._generate_final_sql_query(
            state.get("final_intent", {}), 
            knowledge_data
        )
        
        # Update state for execution
        state.update({
            "flow_state": self.FLOW_STATES["COMPLETED"],
            "final_sql": final_sql,
            "ready_for_execution": True,
            "messages": [AIMessage(content=f"I'm ready to execute your query. Here's the SQL I'll run:\n\n```sql\n{final_sql}\n```\n\nShall I proceed?")]
        })
        
        return state

    def _handle_completed_flow(self, state: Dict[str, Any], user_question: str, knowledge_data: Dict) -> Dict[str, Any]:
        """Handle the completed flow - query has been executed."""
        
        # This would typically be handled by the query executor
        state.update({
            "flow_state": self.FLOW_STATES["COMPLETED"],
            "execution_completed": True,
            "messages": [AIMessage(content="Your query has been executed successfully. Is there anything else you'd like to know?")]
        })
        
        return state

    def _generate_final_sql_query(self, intent_analysis: Dict, knowledge_data: Dict) -> str:
        """Generate the final SQL query based on confirmed intent."""
        
        schema_info = knowledge_data.get("schema", {})
        conversation_context = self._get_conversation_context()
        
        # LOGGING: Track business metrics and context usage
        print(f"\n{'='*80}")
        print(f"CONVERSATIONAL FLOW: Final SQL Generation")
        print(f"{'='*80}")
        
        # Log business metrics being used
        if 'metrics' in schema_info:
            print(f"Business Metrics Available: {len(schema_info['metrics'])}")
            for metric in schema_info['metrics']:
                print(f"  - {metric.get('name', 'Unknown')}: {metric.get('expression', 'No expression')}")
                print(f"    Business Context: {metric.get('business_context', 'None')}")
        
        # Log table business context usage
        for table_name, table_data in schema_info.get('tables', {}).items():
            print(f"\nTable: {table_name}")
            print(f"  Business Context: {table_data.get('business_context', 'None')}")
            
            # Log key columns with business context
            for col_name, col_data in list(table_data.get('columns', {}).items())[:3]:
                if col_data.get('business_context'):
                    print(f"  {col_name}: {col_data.get('business_context', 'None')}")
        
        print(f"Intent Analysis: {intent_analysis}")
        print(f"Conversation Context: {conversation_context}")
        print(f"{'='*80}\n")
        
        prompt = f"""
        You are an expert SQL developer. Generate a well-optimized SQL query based on the confirmed intent analysis.
        
        Intent Analysis:
        {json.dumps(intent_analysis, indent=2)}
        
        Database Schema:
        {json.dumps(schema_info, indent=2)}
        
        Conversation Context:
        {conversation_context}
        
        Generate a SQL query that:
        1. Is syntactically correct
        2. Is optimized for performance
        3. Includes proper joins
        4. Has appropriate filters
        5. Uses proper aggregations if needed
        
        Return only the SQL query, properly formatted.
        """
        
        try:
            print(f"Calling LLM for final SQL generation...")
            response = self.llm.invoke(prompt)
            
            print(f"\n{'='*60}")
            print(f"CONVERSATIONAL FLOW LLM RESPONSE")
            print(f"{'='*60}")
            print(f"Raw Response: {response}")
            print(f"Response Content: {response.content if hasattr(response, 'content') else 'No content'}")
            print(f"{'='*60}\n")
            
            sql = response.content.strip()
            print(f"Final Generated SQL: {sql}")
            return sql
        except Exception as e:
            self.logger.error(f"Error generating final SQL query: {e}")
            print(f"Final SQL Generation Error: {e}")
            return "SELECT * FROM table_name;"

    def _load_conversation_memory(self, conversation_history: List[Dict]) -> None:
        """Load conversation history into memory."""
        try:
            for message in conversation_history:
                if message.get("role") == "user":
                    self.conversation_memory.chat_memory.add_user_message(message.get("content", ""))
                elif message.get("role") == "assistant":
                    self.conversation_memory.chat_memory.add_ai_message(message.get("content", ""))
        except Exception as e:
            self.logger.error(f"Error loading conversation memory: {e}")

    def _get_conversation_context(self) -> str:
        """Get conversation context from memory."""
        try:
            memory_variables = self.conversation_memory.load_memory_variables({})
            return memory_variables.get("conversation_history", "")
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return ""

    def reset_conversation_flow(self) -> None:
        """Reset the conversation flow to initial state."""
        self.conversation_memory.clear()
        self.logger.info("Conversation flow reset")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation."""
        try:
            memory_variables = self.conversation_memory.load_memory_variables({})
            return {
                "conversation_length": len(memory_variables.get("conversation_history", [])),
                "current_context": memory_variables.get("conversation_history", ""),
                "flow_state": getattr(self, "current_flow_state", self.FLOW_STATES["INITIAL"])
            }
        except Exception as e:
            self.logger.error(f"Error getting conversation summary: {e}")
            return {
                "conversation_length": 0,
                "current_context": "",
                "flow_state": self.FLOW_STATES["INITIAL"]
            }
