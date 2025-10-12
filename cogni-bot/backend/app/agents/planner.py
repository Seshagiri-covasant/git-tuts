from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from .domain_error_response import DomainErrorResponseAgent


class Planner:
    def __init__(self, domain_relevance_checker, intent_picker, query_clarification, context_clipper, query_gen, query_clean, query_validator, query_exec, rephraser, checkpoint: SqliteSaver, app_db_util=None, chatbot_db_util=None, chatbot_id: str | None = None):
        self.app_db_util = app_db_util  # For application DB operations
        # For chatbot-related data (chat_bot.db)
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id
        self.workflow = StateGraph(MessagesState)
        
        # Create domain error response agent
        domain_error_response = DomainErrorResponseAgent()
        
        # Pass db utils to nodes if needed
        self.workflow.add_node("Domain_Relevance_Checker", lambda state: domain_relevance_checker.run(
            state, chatbot_id=self.chatbot_id, chatbot_db_util=self.chatbot_db_util))
        self.workflow.add_node("Domain_Error_Response", domain_error_response.run)
        self.workflow.add_node("Intent_Picker", lambda state: intent_picker.run(
            state, chatbot_id=self.chatbot_id, chatbot_db_util=self.chatbot_db_util))
        self.workflow.add_node("Query_Clarification", lambda state: query_clarification.run(
            state, chatbot_id=self.chatbot_id, chatbot_db_util=self.chatbot_db_util))
        self.workflow.add_node("Context_Clipper", lambda state: context_clipper.run(
            state, chatbot_id=self.chatbot_id, chatbot_db_util=self.chatbot_db_util))
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
            """Decide whether to run Query_Clarification or skip to Context_Clipper.

            Heuristic: If a clarification was previously requested (a system
            message containing 'CLARIFICATION_NEEDED:') and we now have a newer
            human/user message after that, treat it as already clarified and
            skip Query_Clarification.
            """
            try:
                msgs = list(state.get("messages", []))
                saw_clar = False
                for msg in reversed(msgs):
                    # Extract content and role in a tolerant way
                    content = None
                    role = None
                    if isinstance(msg, dict):
                        content = msg.get("content") if isinstance(msg.get("content"), str) else None
                        role = msg.get("role")
                    elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                        content = getattr(msg, "content")
                        # Best-effort role inference
                        role = getattr(msg, "type", None) or getattr(msg, "role", None)

                    if isinstance(content, str) and content.startswith("CLARIFICATION_NEEDED:"):
                        saw_clar = True
                        continue

                    # If we've seen clarification and now see a human/user message => skip
                    if saw_clar and (
                        role in ("human", "user") or
                        (hasattr(msg, "__class__") and getattr(msg.__class__, "__name__", "") == "HumanMessage")
                    ):
                        return "Context_Clipper"
            except Exception:
                pass

            return "Query_Clarification"

        def route_after_clarification(state):
            if state.get("clarification_needed", False):
                return END  # Stop workflow, return clarification to user
            else:
                return "Context_Clipper"

        self.workflow.add_edge(START, "Domain_Relevance_Checker")
        self.workflow.add_conditional_edges("Domain_Relevance_Checker", route_after_domain_check)
        self.workflow.add_edge("Domain_Error_Response", END)
        self.workflow.add_conditional_edges("Intent_Picker", route_after_intent)
        self.workflow.add_conditional_edges("Query_Clarification", route_after_clarification)
        self.workflow.add_edge("Context_Clipper", "Query_Generator")
        self.workflow.add_edge("Query_Generator", "Query_Cleaner")
        self.workflow.add_edge("Query_Cleaner", "Query_Validator")
        self.workflow.add_edge("Query_Validator", "Query_Executor")
        self.workflow.add_edge("Query_Executor", "Answer_Rephraser")
        self.workflow.add_edge("Answer_Rephraser", END)

        self.graph = self.workflow.compile(checkpointer=checkpoint)

    def run(self, inputs, config=None):
        return self.graph.stream(inputs, config)