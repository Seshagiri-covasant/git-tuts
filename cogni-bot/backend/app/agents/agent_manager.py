import logging
import re
import json
from .query_generator import QueryGeneratorAgent
from .intent_picker import IntentPickerAgent
from .query_clarification import QueryClarificationAgent
from .context_clipper import ContextClipperAgent
from .query_cleaner import QueryCleaner
from .query_validator import QueryValidatorAgent
from .query_executor import QueryExecutor
from .answer_rephraser import AnswerRephraser
from .domain_relevance_checker import DomainRelevanceCheckerAgent
from .planner import Planner
from .llm_factory import get_llm
from .ba_reporter import generate_llm_ba_summary
from ..utils.exceptions import (
    QueryGenerationException,
    QueryExecutionException,
    QueryCleanupException,
    WorkflowExecutionException,
)


class AgentManager:
    def __init__(self, db_util, checkpoint, template=None, temperature=0.7, bigquery_info=None, chatbot_db_util=None, chatbot_id: str | None = None):
        self.db_util = db_util
        self.checkpoint = checkpoint
        self.temperature = temperature
        self.llm = None
        self.graph = None
        self.bigquery_info = bigquery_info
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id

        if not template:
            raise ValueError(
                "A prompt template must be provided to the AgentManager.")
        self.template = template
        self.processing_status = {
            "current_step": None,
            "progress": 0,
            "message": ""
        }

    def update_processing_status(self, step: str, progress: int, message: str):
        """Update the current processing status for real-time feedback."""
        self.processing_status = {
            "current_step": step,
            "progress": progress,
            "message": message
        }
        logging.info(f"Processing Status: {step} - {progress}% - {message}")

    def get_processing_status(self):
        """Get the current processing status."""
        return self.processing_status

    def get_llm(self, llm_name=None, temperature=None):
        """Gets a configured LLM instance using the factory."""
        current_temperature = temperature if temperature is not None else self.temperature
        # Pass chatbot_id so the factory can resolve LOCAL keys from chatbots.llm_key_settings
        return get_llm(llm_name, temperature=current_temperature, chatbot_id=self.chatbot_id)

    def _prepare_template(self, raw_template: str) -> str:
        """
        Ensure the template includes a '{msg}' placeholder for QueryGeneratorAgent.
        If raw_template already contains '{msg}', leave it as is.
        Otherwise, append the placeholder at the end.
        """
        tpl = raw_template.strip()
        if "{msg}" in tpl:
            return tpl
        return f"{tpl}\n\n{{msg}}"

    def initialize_agents(self, template: str):
        """Initializes all the agents and the graph workflow."""
        prepared_tpl = self._prepare_template(template)

        # Core agents
        domain_relevance_checker = DomainRelevanceCheckerAgent(self.llm, chatbot_db_util=self.chatbot_db_util)
        intent_picker = IntentPickerAgent(self.llm)
        query_clarification = QueryClarificationAgent(self.llm, chatbot_db_util=self.chatbot_db_util)
        context_clipper = ContextClipperAgent()
        query_generator = QueryGeneratorAgent(
            self.llm, self.db_util, prepared_tpl, chatbot_db_util=self.chatbot_db_util, chatbot_id=self.chatbot_id)
        query_cleaner = QueryCleaner()
        query_validator = QueryValidatorAgent(self.llm, self.db_util, chatbot_db_util=self.chatbot_db_util)
        query_executor = QueryExecutor(self.db_util)
        answer_rephraser = AnswerRephraser(query_generator)

        self.planner = Planner(
            domain_relevance_checker,
            intent_picker,
            query_clarification,
            context_clipper,
            query_generator,
            query_cleaner,
            query_validator,
            query_executor,
            answer_rephraser,
            self.checkpoint,
            app_db_util=self.db_util,
            chatbot_db_util=self.chatbot_db_util,
            chatbot_id=self.chatbot_id
        )
        self.graph = self.planner.graph

    def execute(self, conv_id: str, request: str, llm_name: str = None, template: str = None, temperature: float = None):
        """
        Executes the full agent workflow for a given user request, faithfully porting the original logic.
        """
        current_temperature = temperature if temperature is not None else self.temperature
        logging.debug(
            f"Executing agent for conv_id: {conv_id}, llm_name: {llm_name}, temp: {current_temperature}")

        user_message = request
        inputs = {"messages": [{"role": "human", "content": user_message}]}
        config = {"configurable": {"thread_id": conv_id}}

        results = []
        final_sql = None
        raw_result_set = None
        ba_summary = None

        try:
            self.update_processing_status(
                "initializing", 10, "Initializing AI model...")
            self.llm = self.get_llm(llm_name, temperature=current_temperature)
            raw_tpl = template or self.template
            self.update_processing_status(
                "preparing", 20, "Preparing AI agents...")
            self.initialize_agents(raw_tpl)

            # Fixed progress milestones per node to avoid overshooting 100%
            progress_map = {
                "initializing": 10,
                "preparing": 20,
                "Intent_Picker": 30,
                "Query_Clarification": 40,
                "Context_Clipper": 50,
                "Query_Generator": 65,
                "Query_Cleaner": 75,
                "Query_Validator": 85,
                "Query_Executor": 95,
                "Answer_Rephraser": 98,
            }
            for output in self.graph.stream(inputs, config):
                if not isinstance(output, dict) or not output:
                    continue

                node_name = list(output.keys())[0]
                node_output = output[node_name]
                logging.debug(f"Output from node '{node_name}': {node_output}")

                # Update status based on the node that just ran (use fixed progress map)
                if node_name in progress_map:
                    progress = progress_map[node_name]
                    if node_name == "Intent_Picker":
                        self.update_processing_status("analyzing", progress, "Identifying intent and relevant entities...")
                    elif node_name == "Query_Clarification":
                        self.update_processing_status("clarifying", progress, "Checking if question needs clarification...")
                    elif node_name == "Context_Clipper":
                        self.update_processing_status("context", progress, "Preparing relevant schema context...")
                    elif node_name == "Query_Generator":
                        self.update_processing_status("generating", progress, "Generating SQL query...")
                    elif node_name == "Query_Cleaner":
                        self.update_processing_status("cleaning", progress, "Validating and cleaning query...")
                    elif node_name == "Query_Validator":
                        self.update_processing_status("validating", progress, "Validating SQL against schema...")
                    elif node_name == "Query_Executor":
                        self.update_processing_status("executing", progress, "Executing query against database...")
                    elif node_name == "Answer_Rephraser":
                        self.update_processing_status("formatting", progress, "Formatting final answer...")

                # Store the result from this step
                messages = node_output.get("messages", ["No content from agent node"]) if isinstance(
                    node_output, dict) else [str(node_output)]
                results.append({"step": node_name, "result": messages})

            # Extract final natural language result from the last step
            final_result_message_obj = results[-1].get(
                "result", ["No content from agent response"])[-1]
            final_result = final_result_message_obj.content if hasattr(
                final_result_message_obj, 'content') else str(final_result_message_obj)

            self.update_processing_status(
                "completed", 100, "Processing completed")

            # Try to extract the raw result set (JSON)
            for step in results:
                if step.get("step") == "Query_Executor" and step.get("result"):
                    try:
                        # The result from the executor is a JSON string of the data
                        data_string = step["result"][-1].content if hasattr(
                            step["result"][-1], 'content') else str(step["result"][-1])
                        parsed_data = json.loads(data_string)
                        
                        # Handle the new format: {"data": [...], "metadata": {...}}
                        if isinstance(parsed_data, dict) and "data" in parsed_data:
                            raw_result_set = parsed_data["data"]
                        # Handle the old format: direct list
                        elif isinstance(parsed_data, list) and (not parsed_data or "error" not in parsed_data[0]):
                            raw_result_set = parsed_data
                    except (json.JSONDecodeError, IndexError, TypeError):
                        pass  # Not a valid JSON result set

            # Do not auto-generate BA summary here. BA Insights should be triggered explicitly from UI.
            ba_summary = None

        except (QueryGenerationException, QueryExecutionException, QueryCleanupException) as e:
            self.update_processing_status("error", 100, f"Error: {str(e)}")
            raise e
        except Exception as e:
            self.update_processing_status(
                "error", 100, f"Unexpected error: {str(e)}")
            raise WorkflowExecutionException(e)

        # Robustly extract the final cleaned SQL query, as per original logic
        # Prioritize the output of the Query_Validator node (final validated SQL)
        for step in results:
            if step.get("step") == "Query_Validator" and step.get("result"):
                sql_obj = step["result"][-1]
                final_sql = sql_obj.content if hasattr(
                    sql_obj, 'content') else str(sql_obj)
                break

        # Fallback to Query_Cleaner if validator failed or was missed
        if final_sql is None:
            for step in results:
                if step.get("step") == "Query_Cleaner" and step.get("result"):
                    sql_obj = step["result"][-1]
                    final_sql = sql_obj.content if hasattr(
                        sql_obj, 'content') else str(sql_obj)
                    break

        # Fallback to Query_Generator if both cleaner and validator failed
        if final_sql is None:
            for step in results:
                if step.get("step") == "Query_Generator" and step.get("result"):
                    raw_sql_obj = step["result"][-1]
                    raw_sql = raw_sql_obj.content if hasattr(
                        raw_sql_obj, 'content') else str(raw_sql_obj)
                    final_sql = re.sub(r"```sql\s*|\s*```",
                                       "", raw_sql, flags=re.I | re.S).strip()
                    break

        logging.debug(f"Final extracted SQL: {final_sql}")

        return {
            "final_result": final_result,
            "cleaned_query": final_sql,
            "raw_result_set": raw_result_set,
            "ba_summary": ba_summary
        }
