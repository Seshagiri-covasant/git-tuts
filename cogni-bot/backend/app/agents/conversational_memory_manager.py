"""
Conversational Memory Manager

This agent manages conversation memory and context for the chatbot.
"""

import json
from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferMemory
from app.repositories.chatbot_db_util import ChatbotDbUtil


class ConversationalMemoryManager:
    """
    Manages conversation memory and context for the chatbot.
    """
    
    def __init__(self, chatbot_db_util: ChatbotDbUtil, chatbot_id: str):
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    
    def load_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Load conversation history from database.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List of conversation messages
        """
        try:
            if not self.chatbot_db_util or not conversation_id:
                return []
            
            # Get conversation history from database
            # This is a simplified implementation - you may need to adjust based on your DB schema
            history = []
            
            # For now, return empty history
            # In a real implementation, you would query the database for conversation messages
            return history
            
        except Exception as e:
            print(f"[ConversationalMemoryManager] Error loading conversation history: {e}")
            return []
    
    def update_conversation_memory(self, conversation_history: List[Dict[str, Any]]) -> None:
        """
        Update the conversation memory with new history.
        
        Args:
            conversation_history: List of conversation messages
        """
        try:
            # Clear existing memory
            self.memory.clear()
            
            # Add messages to memory
            for message in conversation_history:
                role = message.get('role', 'user')
                content = message.get('content', '')
                
                if role == 'user':
                    self.memory.chat_memory.add_user_message(content)
                elif role == 'assistant':
                    self.memory.chat_memory.add_ai_message(content)
                    
        except Exception as e:
            print(f"[ConversationalMemoryManager] Error updating memory: {e}")
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation.
        
        Returns:
            Conversation summary string
        """
        try:
            messages = self.memory.chat_memory.messages
            if not messages:
                return "No conversation history."
            
            # Create a simple summary
            user_messages = [msg.content for msg in messages if hasattr(msg, 'content') and 'user' in str(type(msg)).lower()]
            ai_messages = [msg.content for msg in messages if hasattr(msg, 'content') and 'ai' in str(type(msg)).lower()]
            
            summary = f"Conversation has {len(user_messages)} user messages and {len(ai_messages)} AI responses."
            return summary
            
        except Exception as e:
            print(f"[ConversationalMemoryManager] Error getting summary: {e}")
            return "Error retrieving conversation summary."
    
    def reset_conversation(self) -> None:
        """Reset the conversation memory."""
        try:
            self.memory.clear()
        except Exception as e:
            print(f"[ConversationalMemoryManager] Error resetting conversation: {e}")
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation memory.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        try:
            if role == 'user':
                self.memory.chat_memory.add_user_message(content)
            elif role == 'assistant':
                self.memory.chat_memory.add_ai_message(content)
        except Exception as e:
            print(f"[ConversationalMemoryManager] Error adding message: {e}")

