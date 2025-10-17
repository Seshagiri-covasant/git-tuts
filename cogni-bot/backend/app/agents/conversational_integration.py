import logging
import json
from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from ..utils.exceptions import QueryGenerationException
from ..repositories.chatbot_db_util import ChatbotDbUtil
from ..repositories.app_db_util import AppDbUtil
# from .enhanced_agent_manager import EnhancedAgentManager  # Deleted agent
from .agent_manager import AgentManager


class ConversationalIntegration:
    """
    Integration layer that provides seamless switching between traditional and enhanced
    conversational intent analysis. Allows gradual migration and A/B testing.
    """
    
    def __init__(self, db_util=None, checkpoint=None, template=None, chatbot_db_util: ChatbotDbUtil = None, chatbot_id: str = None):
        self.db_util = db_util
        self.checkpoint = checkpoint
        self.template = template
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id
        self.logger = logging.getLogger(__name__)
        
        # Initialize both agent managers
        self.traditional_manager = None
        self.enhanced_manager = None
        
        # Configuration - Disabled enhanced flow since agents were deleted
        self.use_enhanced_flow = False  # Set to False to use traditional flow
        self.conversation_mode = "traditional"  # "enhanced" or "traditional"

    def initialize_agents(self, template: str, llm_config: Dict[str, Any] = None) -> None:
        """Initialize the appropriate agent manager based on configuration."""
        try:
            if self.use_enhanced_flow:
                # Initialize enhanced conversational flow
                self.enhanced_manager = EnhancedAgentManager(
                    db_util=self.db_util,
                    checkpoint=self.checkpoint,
                    template=template,
                    chatbot_db_util=self.chatbot_db_util,
                    chatbot_id=self.chatbot_id
                )
                
                if llm_config:
                    self.enhanced_manager.initialize_agents(llm_config)
                else:
                    # Use default LLM configuration
                    default_config = {
                        "provider": "openai",
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.7
                    }
                    self.enhanced_manager.initialize_agents(default_config)
                
                self.conversation_mode = "enhanced"
                self.logger.info("Enhanced conversational flow initialized")
                
            else:
                # Initialize traditional flow
                self.traditional_manager = AgentManager(
                    db_util=self.db_util,
                    checkpoint=self.checkpoint,
                    template=template,
                    chatbot_db_util=self.chatbot_db_util,
                    chatbot_id=self.chatbot_id
                )
                
                self.traditional_manager.initialize_agents(template)
                self.conversation_mode = "traditional"
                self.logger.info("Traditional conversational flow initialized")
                
        except Exception as e:
            self.logger.error(f"Error initializing agents: {e}")
            raise QueryGenerationException(f"Failed to initialize agents: {e}")

    def process_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a conversational query using the appropriate agent manager.
        
        Args:
            state: Current conversation state containing:
                - user_question: Current user query
                - conversation_history: Previous conversation messages
                - knowledge_data: Database schema and context
                - agent_state: Current agent state
                
        Returns:
            Updated state with conversational response and next steps
        """
        try:
            if self.conversation_mode == "enhanced" and self.enhanced_manager:
                return self._process_enhanced_query(state)
            elif self.conversation_mode == "traditional" and self.traditional_manager:
                return self._process_traditional_query(state)
            else:
                raise QueryGenerationException("No agent manager initialized")
                
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            raise QueryGenerationException(f"Query processing failed: {e}")

    def _process_enhanced_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process query using enhanced conversational flow."""
        try:
            # Use enhanced agent manager
            result = self.enhanced_manager.process_conversational_query(state)
            
            # Add enhanced flow metadata
            result.update({
                "conversation_mode": "enhanced",
                "flow_manager_initialized": self.enhanced_manager.flow_manager is not None,
                "agent_status": self.enhanced_manager.get_agent_status()
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in enhanced query processing: {e}")
            raise QueryGenerationException(f"Enhanced query processing failed: {e}")

    def _process_traditional_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process query using traditional conversational flow."""
        try:
            # Use traditional agent manager
            result = self.traditional_manager.process_query(state)
            
            # Add traditional flow metadata
            result.update({
                "conversation_mode": "traditional",
                "agent_initialized": self.traditional_manager is not None
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in traditional query processing: {e}")
            raise QueryGenerationException(f"Traditional query processing failed: {e}")

    def switch_conversation_mode(self, mode: str) -> None:
        """Switch between enhanced and traditional conversation modes."""
        if mode not in ["enhanced", "traditional"]:
            raise ValueError("Mode must be 'enhanced' or 'traditional'")
        
        self.conversation_mode = mode
        self.use_enhanced_flow = (mode == "enhanced")
        self.logger.info(f"Switched to {mode} conversation mode")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary from the active manager."""
        try:
            if self.conversation_mode == "enhanced" and self.enhanced_manager:
                return self.enhanced_manager.get_conversation_summary()
            elif self.conversation_mode == "traditional" and self.traditional_manager:
                return {
                    "conversation_mode": "traditional",
                    "agent_initialized": self.traditional_manager is not None
                }
            else:
                return {"error": "No active agent manager"}
                
        except Exception as e:
            self.logger.error(f"Error getting conversation summary: {e}")
            return {"error": str(e)}

    def reset_conversation(self) -> None:
        """Reset conversation in the active manager."""
        try:
            if self.conversation_mode == "enhanced" and self.enhanced_manager:
                self.enhanced_manager.reset_conversation()
            elif self.conversation_mode == "traditional" and self.traditional_manager:
                # Traditional manager doesn't have reset method, but we can clear memory
                if hasattr(self.traditional_manager, 'memory'):
                    self.traditional_manager.memory.clear()
            
            self.logger.info("Conversation reset")
            
        except Exception as e:
            self.logger.error(f"Error resetting conversation: {e}")

    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of the active agent manager."""
        try:
            if self.conversation_mode == "enhanced" and self.enhanced_manager:
                return self.enhanced_manager.get_agent_status()
            elif self.conversation_mode == "traditional" and self.traditional_manager:
                return {
                    "conversation_mode": "traditional",
                    "agent_initialized": self.traditional_manager is not None,
                    "processing_status": getattr(self.traditional_manager, 'processing_status', {})
                }
            else:
                return {"error": "No active agent manager"}
                
        except Exception as e:
            self.logger.error(f"Error getting agent status: {e}")
            return {"error": str(e)}

    def validate_sql_query(self, sql_query: str, knowledge_data: Dict) -> Dict[str, Any]:
        """Validate SQL query using the active manager."""
        try:
            if self.conversation_mode == "enhanced" and self.enhanced_manager:
                return self.enhanced_manager.validate_sql_query(sql_query, knowledge_data)
            else:
                # Fallback validation
                return self._basic_sql_validation(sql_query)
                
        except Exception as e:
            self.logger.error(f"Error validating SQL query: {e}")
            return {"valid": False, "error": str(e)}

    def execute_sql_query(self, sql_query: str, knowledge_data: Dict) -> Dict[str, Any]:
        """Execute SQL query using the active manager."""
        try:
            if self.conversation_mode == "enhanced" and self.enhanced_manager:
                return self.enhanced_manager.execute_sql_query(sql_query, knowledge_data)
            else:
                # Fallback execution
                return self._basic_sql_execution(sql_query)
                
        except Exception as e:
            self.logger.error(f"Error executing SQL query: {e}")
            return {"success": False, "error": str(e)}

    def _basic_sql_validation(self, sql_query: str) -> Dict[str, Any]:
        """Basic SQL validation fallback."""
        try:
            if not sql_query.strip():
                return {"valid": False, "error": "Empty SQL query"}
            
            # Check for dangerous operations
            dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
            sql_upper = sql_query.upper()
            
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return {
                        "valid": False, 
                        "error": f"Dangerous operation detected: {keyword}",
                        "suggestion": "Only SELECT queries are allowed"
                    }
            
            return {"valid": True, "message": "SQL query is valid"}
            
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {e}"}

    def _basic_sql_execution(self, sql_query: str) -> Dict[str, Any]:
        """Basic SQL execution fallback."""
        try:
            if not self.db_util:
                return {"success": False, "error": "Database utility not initialized"}
            
            result = self.db_util.execute_query(sql_query)
            return {
                "success": True,
                "result": result,
                "query": sql_query,
                "row_count": len(result) if isinstance(result, list) else 0
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "query": sql_query}
