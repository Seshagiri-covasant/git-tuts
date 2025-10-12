from langchain_core.messages import HumanMessage


class DomainErrorResponseAgent:
    def __init__(self):
        pass

    def run(self, state: dict) -> dict:
        """Handle domain relevance check failure by returning the error message."""
        print("[Domain_Error_Response] Handling domain check failure")
        
        # Get the error message from the state
        error_message = state.get("domain_error_message", "This question is not relevant to the database domain.")
        
        # Add the error message as a human message (this will be displayed to the user)
        state["messages"].append(HumanMessage(content=error_message))
        
        print(f"[Domain_Error_Response] Returning error message: {error_message}")
        return state
