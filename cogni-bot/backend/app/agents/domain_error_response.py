"""
Domain Error Response Agent

This agent handles domain-related errors and provides appropriate responses.
"""

from typing import Dict, Any


class DomainErrorResponseAgent:
    """
    Handles domain-related errors and provides appropriate responses.
    """
    
    def __init__(self):
        self.error_messages = {
            "domain_not_relevant": "I'm sorry, but your question doesn't seem to be related to the available data. Could you please ask a question about the data in our system?",
            "insufficient_context": "I need more information to help you. Could you please provide more details about what you're looking for?",
            "ambiguous_question": "Your question could be interpreted in several ways. Could you please be more specific?",
            "no_data_found": "I couldn't find any data matching your criteria. Would you like to try a different approach?"
        }
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle domain error response.
        
        Args:
            state: Current state containing error information
            
        Returns:
            Updated state with error response
        """
        try:
            error_type = state.get('error_type', 'domain_not_relevant')
            error_message = self.error_messages.get(error_type, self.error_messages['domain_not_relevant'])
            
            return {
                **state,
                'messages': [error_message],
                'error_handled': True,
                'domain_error': True
            }
            
        except Exception as e:
            print(f"[DomainErrorResponseAgent] Error: {e}")
            return {
                **state,
                'messages': ["I encountered an error processing your request. Please try again."],
                'error_handled': True,
                'domain_error': True
            }

