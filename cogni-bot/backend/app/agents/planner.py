from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict, List, Dict, Any
from .domain_error_response import DomainErrorResponseAgent
from .human_approval_agent import HumanApprovalAgent

class CustomState(TypedDict):
    messages: List[Any]
    user_question: str
    conversation_history: List[Dict[str, Any]]
    knowledge_data: Dict[str, Any]
    intent: Dict[str, Any]
    clarification_needed: bool
    clarification_question: str
    gathered_info: Dict[str, Any]
    reasoning: str
    conversation_phase: str
    summary: str
    error: str
    # SQL-related fields
    generated_sql: str
    sql_query: str
    sql: str
    query: str
    final_sql: str
    forbidden_sql: bool
    # Human approval fields
    human_approval_needed: bool
    intent_approved: bool
    approval_request: Dict[str, Any]
    clarification_questions: List[Dict[str, Any]]
    similar_columns: List[Dict[str, Any]]
    ambiguity_analysis: Dict[str, Any]
    human_response: Dict[str, Any]


class Planner:
    def __init__(self, domain_relevance_checker, intent_picker, query_clarification, context_clipper, query_gen, query_clean, query_validator, query_exec, rephraser, checkpoint: SqliteSaver, app_db_util=None, chatbot_db_util=None, chatbot_id: str | None = None, conversational_intent_analyzer=None, human_approval_agent=None):
        self.app_db_util = app_db_util  # For application DB operations
        # For chatbot-related data (chat_bot.db)
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id
        self.workflow = StateGraph(CustomState)
        
        # Create domain error response agent
        domain_error_response = DomainErrorResponseAgent()
        
        # Pass db utils to nodes if needed
        self.workflow.add_node("Domain_Relevance_Checker", lambda state: domain_relevance_checker.run(
            state, chatbot_id=self.chatbot_id, chatbot_db_util=self.chatbot_db_util))
        self.workflow.add_node("Domain_Error_Response", domain_error_response.run)
        self.workflow.add_node("Intent_Picker", lambda state: intent_picker.run(state))
        self.workflow.add_node("Conversational_Intent_Analyzer", lambda state: self._run_conversational_intent_analyzer(state, conversational_intent_analyzer))
        self.workflow.add_node("Human_Approval", lambda state: self._run_human_approval(state, human_approval_agent))
        self.workflow.add_node("Query_Clarification", lambda state: query_clarification.run(state))  # Use existing query_clarification
        self.workflow.add_node("Context_Clipper", lambda state: context_clipper.run(state))
        self.workflow.add_node("Query_Generator", lambda state: query_gen.run(
            state, app_db_util=self.app_db_util, chatbot_db_util=self.chatbot_db_util))
        self.workflow.add_node("Query_Cleaner", query_clean.run)
        self.workflow.add_node("Query_Validator", lambda state: query_validator.run(
            state, app_db_util=self.app_db_util, chatbot_db_util=self.chatbot_db_util))
        self.workflow.add_node("Query_Executor", lambda state: query_exec.run(
            state, app_db_util=self.app_db_util))
        self.workflow.add_node("Answer_Rephraser", lambda state: rephraser.run(
            state, app_db_util=self.app_db_util, chatbot_db_util=self.chatbot_db_util))

        # Define conditional routing functions
        def route_after_domain_check(state):
            if state.get("domain_check_failed", False):
                return "Domain_Error_Response"
            else:
                return "Intent_Picker"

        def route_after_intent(state):
            """Go to Conversational_Intent_Analyzer first for conversational analysis."""
            print(f"[Planner] Routing after Intent_Picker to Conversational_Intent_Analyzer")
            return "Conversational_Intent_Analyzer"

        def route_after_conversational_intent(state):
            """After conversational analysis, go to Human_Approval."""
            print(f"[Planner] Routing after Conversational_Intent_Analyzer to Human_Approval")
            return "Human_Approval"
        
        def route_after_human_approval(state):
            """After human approval, check if approval is needed or proceed."""
            if state.get("human_approval_needed", False):
                return END  # Stop workflow, return approval request to user
            else:
                return "Query_Clarification"

        def route_after_query_clarification(state):
            if state.get("clarification_needed", False):
                return END  # Stop workflow, return clarification to user
            else:
                return "Context_Clipper"

        self.workflow.add_edge(START, "Domain_Relevance_Checker")
        self.workflow.add_conditional_edges("Domain_Relevance_Checker", route_after_domain_check)
        self.workflow.add_edge("Domain_Error_Response", END)
        self.workflow.add_conditional_edges("Intent_Picker", route_after_intent)
        self.workflow.add_conditional_edges("Conversational_Intent_Analyzer", route_after_conversational_intent)
        self.workflow.add_conditional_edges("Human_Approval", route_after_human_approval)
        self.workflow.add_conditional_edges("Query_Clarification", route_after_query_clarification)
        self.workflow.add_edge("Context_Clipper", "Query_Generator")
        self.workflow.add_edge("Query_Generator", "Query_Cleaner")
        self.workflow.add_edge("Query_Cleaner", "Query_Validator")
        self.workflow.add_edge("Query_Validator", "Query_Executor")
        self.workflow.add_edge("Query_Executor", "Answer_Rephraser")
        self.workflow.add_edge("Answer_Rephraser", END)

        self.graph = self.workflow.compile(checkpointer=checkpoint)

    def _run_conversational_intent_analyzer(self, state, conversational_intent_analyzer):
        """Helper method to run Conversational_Intent_Analyzer with debug logging."""
        print(f"[Planner] About to run Conversational_Intent_Analyzer")
        if conversational_intent_analyzer:
            result = conversational_intent_analyzer.analyze_intent(state)
            print(f"[Planner] Conversational_Intent_Analyzer completed, clarification_needed: {result.get('clarification_needed', False)}")
            return result
        else:
            print(f"[Planner] No conversational_intent_analyzer provided, skipping")
            return state
    
    def _run_human_approval(self, state, human_approval_agent):
        """Helper method to run Human_Approval with debug logging."""
        print(f"[Planner] About to run Human_Approval")
        if human_approval_agent:
            result = human_approval_agent.run(state)
            print(f"[Planner] Human_Approval completed, human_approval_needed: {result.get('human_approval_needed', False)}")
            return result
        else:
            print(f"[Planner] No human_approval_agent provided, skipping")
            return state

    def _run_query_clarification(self, state, query_clarification):
        """Helper method to run Query_Clarification with debug logging."""
        print(f"[Planner] About to run Query_Clarification")
        result = query_clarification.run(state)
        print(f"[Planner] Query_Clarification completed, clarification_needed: {result.get('clarification_needed', False)}")
        return result

    def run(self, inputs, config=None):
        return self.graph.stream(inputs, config)