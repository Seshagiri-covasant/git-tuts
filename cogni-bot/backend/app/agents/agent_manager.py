import logging
import re
import json
from datetime import datetime
from typing import Dict, Any, List
from langchain.memory import ConversationBufferMemory
from .query_generator import QueryGeneratorAgent
from .intent_picker import AdvancedIntentPicker
from .query_clarification import ConversationalClarificationAgent
from .context_clipper import ConversationalContextClipper
from .query_cleaner import QueryCleaner
from .query_validator import QueryValidatorAgent
from .query_executor import QueryExecutor
from .answer_rephraser import AnswerRephraser
from .domain_relevance_checker import DomainRelevanceCheckerAgent
from .conversational_intent_analyzer import ConversationalIntentAnalyzer
from .conversational_memory_manager import ConversationalMemoryManager
from .planner import Planner
from .llm_factory import get_llm
from .ba_reporter import generate_llm_ba_summary
# ConversationalIntegration imported lazily to avoid circular import
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
        self.memory = ConversationBufferMemory(return_messages=True)
        self.graph = None
        self.bigquery_info = bigquery_info
        self.chatbot_db_util = chatbot_db_util
        self.chatbot_id = chatbot_id
        
        # Initialize conversational memory manager
        self.memory_manager = ConversationalMemoryManager(chatbot_db_util, chatbot_id)
        
        # Initialize conversational integration for enhanced flow (lazy import)
        self.conversational_integration = None

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

    def enable_enhanced_conversational_flow(self, llm_config: Dict[str, Any] = None) -> None:
        """Enable enhanced conversational flow with human-like dialogue."""
        try:
            # Lazy import to avoid circular dependency
            if self.conversational_integration is None:
                from .conversational_integration import ConversationalIntegration
                self.conversational_integration = ConversationalIntegration(
                    db_util=self.db_util,
                    checkpoint=self.checkpoint,
                    template=self.template,
                    chatbot_db_util=self.chatbot_db_util,
                    chatbot_id=self.chatbot_id
                )
            
            self.conversational_integration.initialize_agents(
                template=self.template,
                llm_config=llm_config
            )
            self.logger.info("Enhanced conversational flow enabled")
        except Exception as e:
            self.logger.error(f"Error enabling enhanced conversational flow: {e}")
            raise QueryGenerationException(f"Failed to enable enhanced conversational flow: {e}")

    def initialize_agents(self, template: str):
        """Initializes all the agents and the graph workflow."""
        prepared_tpl = self._prepare_template(template)

        # Core agents
        domain_relevance_checker = DomainRelevanceCheckerAgent(self.llm, chatbot_db_util=self.chatbot_db_util)
        intent_picker = AdvancedIntentPicker(self.llm)
        conversational_intent_analyzer = ConversationalIntentAnalyzer(self.llm)
        query_clarification = ConversationalClarificationAgent(self.llm, chatbot_db_util=self.chatbot_db_util)
        context_clipper = ConversationalContextClipper(self.llm)
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
            chatbot_id=self.chatbot_id,
            conversational_intent_analyzer=conversational_intent_analyzer
        )
        self.graph = self.planner.graph

    def _load_conversation_memory(self, conv_id: str):
        """
        Load conversation history from database into LangChain memory.
        """
        try:
            if not self.chatbot_db_util:
                print(f"[AgentManager] No chatbot_db_util available, using empty memory")
                return
            
            # Load conversation history using memory manager
            conversation_history = self.memory_manager.load_conversation_history(conv_id)
            self.memory_manager.update_conversation_memory(conversation_history)
            
            # Also update the legacy memory for backward compatibility
            self.memory.clear()
            for message in conversation_history:
                if message.get("role") == "user":
                    self.memory.chat_memory.add_user_message(message["content"])
                elif message.get("role") == "assistant":
                    self.memory.chat_memory.add_ai_message(message["content"])
            
            print(f"[AgentManager] Loaded {len(conversation_history)} interactions into memory")
                
        except Exception as e:
            print(f"[AgentManager] Error loading conversation memory: {e}")
            # Continue with empty memory

    def _load_schema_info(self):
        """
        Load schema information for the agents.
        """
        try:
            if not self.chatbot_db_util:
                print(f"[AgentManager] No chatbot_db_util available, using empty schema")
                return {}
            
            # Get chatbot information
            chatbot = self.chatbot_db_util.get_chatbot(self.chatbot_id)
            if not chatbot:
                print(f"[AgentManager] No chatbot found for ID: {self.chatbot_id}")
                return {}
            
            # Get semantic schema information (includes metrics and business context)
            from app.services.chatbot_service import get_semantic_schema_service
            try:
                semantic_schema = get_semantic_schema_service(self.chatbot_id)
                print(f"[AgentManager] Loaded semantic schema with {len(semantic_schema.get('tables', {}))} tables")
                print(f"[AgentManager] Semantic schema metrics: {len(semantic_schema.get('metrics', []))} metrics")
                
                # Convert semantic schema to the format expected by agents
                schema_data = {
                    "chatbot_id": self.chatbot_id,
                    "schema": semantic_schema,
                    "schema_summary": f"Semantic schema with {len(semantic_schema.get('tables', {}))} tables and {len(semantic_schema.get('metrics', []))} metrics",
                    "database_type": "semantic",
                    "database_url": "semantic_schema"
                }
                return schema_data
            except Exception as e:
                print(f"[AgentManager] Failed to load semantic schema: {e}")
                # Fallback to raw schema
                from app.services.chatbot_service import get_schema_service
                schema_data = get_schema_service(self.chatbot_id)
                print(f"[AgentManager] Fallback to raw schema with {len(schema_data.get('schema', {}).get('tables', []))} tables")
                return schema_data
            
        except Exception as e:
            print(f"[AgentManager] Error loading schema info: {e}")
            return {}

    def execute(self, conv_id: str, request: str, llm_name: str = None, template: str = None, temperature: float = None):
        """
        Executes the full agent workflow for a given user request, faithfully porting the original logic.
        """
        current_temperature = temperature if temperature is not None else self.temperature
        logging.debug(
            f"Executing agent for conv_id: {conv_id}, llm_name: {llm_name}, temp: {current_temperature}")

        # Load conversation history into LangChain memory
        self._load_conversation_memory(conv_id)
        
        # Add the new user request to memory
        self.memory.chat_memory.add_user_message(request)
        
        # Get the conversation history from memory
        conversation_history = self.memory.chat_memory.messages
        print(f"[AgentManager] Retrieved {len(conversation_history)} messages from LangChain memory")
        
        # Load schema information for the agents
        schema_info = self._load_schema_info()
        
        # COMPREHENSIVE LOGGING: Schema data sent to LLM
        print(f"AGENT DEBUG: Schema data being sent to LLM")
        print(f"Schema Info Keys: {list(schema_info.keys()) if schema_info else 'None'}")
            
        if schema_info and 'schema' in schema_info:
            schema = schema_info['schema']
            # Handle both dict and list formats for tables
            tables_data = schema.get('tables', {})
            if isinstance(tables_data, dict):
                print(f"Schema Tables: {list(tables_data.keys())}")
            elif isinstance(tables_data, list):
                print(f"Schema Tables: {[t.get('name', 'Unknown') for t in tables_data]}")
            else:
                print(f"Schema Tables: {type(tables_data)} - {tables_data}")
            
            # Log business metrics
            if 'metrics' in schema:
                print(f"Business Metrics: {len(schema['metrics'])} metrics")
                for metric in schema['metrics']:
                    print(f"  - {metric.get('name', 'Unknown')}: {metric.get('expression', 'No expression')}")
            
            # Log table details with business context
            if isinstance(tables_data, dict):
                for table_name, table_data in tables_data.items():
                    print(f"\nTable: {table_name}")
                    print(f"  Business Context: {table_data.get('business_context', 'None')}")
                    print(f"  Description: {table_data.get('description', 'None')}")
                    
                    # Log column details
                    columns = table_data.get('columns', {})
                    print(f"  Columns ({len(columns)}):")
                    for col_name, col_data in list(columns.items())[:5]:  # Show first 5 columns
                        print(f"    - {col_name}:")
                        print(f"      Description: {col_data.get('description', 'None')}")
                        print(f"      Business Context: {col_data.get('business_context', 'None')}")
                        print(f"      Exclude Column: {col_data.get('exclude_column', False)}")
                    
                    if len(columns) > 5:
                        print(f"    ... and {len(columns) - 5} more columns")
            
            print(f"{'='*80}\n")
        
        user_message = request
        inputs = {
            "messages": conversation_history,
            "user_question": request,
            "conversation_history": [{"role": "user", "content": request}],
            "knowledge_data": schema_info
        }
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
                # Check if result has sql_query or generated_sql
                if isinstance(step["result"], dict):
                    final_sql = step["result"].get("sql_query") or step["result"].get("generated_sql")
                else:
                    sql_obj = step["result"][-1]
                    final_sql = sql_obj.content if hasattr(
                        sql_obj, 'content') else str(sql_obj)
                if final_sql:
                    break

        # Fallback to Query_Cleaner if validator failed or was missed
        if final_sql is None:
            for step in results:
                if step.get("step") == "Query_Cleaner" and step.get("result"):
                    # Check if result has sql_query or generated_sql
                    if isinstance(step["result"], dict):
                        final_sql = step["result"].get("sql_query") or step["result"].get("generated_sql")
                    else:
                        sql_obj = step["result"][-1]
                        final_sql = sql_obj.content if hasattr(
                            sql_obj, 'content') else str(sql_obj)
                    if final_sql:
                        break

        # Fallback to Query_Generator if both cleaner and validator failed
        if final_sql is None:
            for step in results:
                if step.get("step") == "Query_Generator" and step.get("result"):
                    # Check if result has sql_query or generated_sql
                    if isinstance(step["result"], dict):
                        final_sql = step["result"].get("sql_query") or step["result"].get("generated_sql")
                    else:
                        raw_sql_obj = step["result"][-1]
                        raw_sql = raw_sql_obj.content if hasattr(
                            raw_sql_obj, 'content') else str(raw_sql_obj)
                        final_sql = re.sub(r"```sql\s*|\s*```",
                                           "", raw_sql, flags=re.I | re.S).strip()
                    if final_sql:
                        break

        logging.debug(f"Final extracted SQL: {final_sql}")

        # Collect debug information from each step
        debug_steps = []
        for step in results:
            node_name = step.get("step")
            if not node_name:
                continue

            step_info = {
                "step": node_name,
                "status": "completed",
                "details": {},
                "timestamp": step.get("timestamp", "")
            }

            # Extract intent information
            if node_name == "Intent_Picker":
                try:
                    for msg in step.get("result", []):
                        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.startswith("INTENT:"):
                            intent = json.loads(msg.content[7:])
                            step_info["details"]["intent"] = intent
                            print(f"[AgentManager] Captured intent: {intent}")
                            break
                except Exception as e:
                    print(f"[AgentManager] Error extracting intent: {e}")
                    pass

            # Extract query generation and validation information
            elif node_name in ["Query_Generator", "Query_Validator", "Query_Cleaner"]:
                try:
                    print(f"[AgentManager] Processing {node_name} for SQL extraction")
                    
                    # Check if result is a dictionary with SQL keys
                    if isinstance(step.get("result"), dict):
                        result_dict = step.get("result")
                        sql_content = result_dict.get("sql_query") or result_dict.get("generated_sql")
                        if sql_content:
                            step_info["details"]["generatedSQL"] = sql_content
                            print(f"[AgentManager] Found SQL in {node_name} dict: {sql_content[:100]}...")
                    else:
                        # Fallback to checking messages array
                        for msg in step.get("result", []):
                            if hasattr(msg, "content") and isinstance(msg.content, str):
                                print(f"[AgentManager] Checking content: {msg.content[:100]}...")
                                if "SELECT" in msg.content.upper():
                                    # Only capture SQL from Query_Generator, not from other steps
                                    if node_name == "Query_Generator":
                                        step_info["details"]["generatedSQL"] = msg.content
                                        print(f"[AgentManager] Found SQL in Query_Generator: {msg.content[:100]}...")
                                    break
                except Exception as e:
                    print(f"[AgentManager] Error extracting SQL from {node_name}: {e}")
                    pass

            # Extract clarification information
            elif node_name == "Query_Clarification":
                try:
                    messages = step.get("result", [])
                    clarification_needed = any(msg.content.startswith("CLARIFICATION_NEEDED:") for msg in messages if hasattr(msg, "content"))
                    step_info["details"]["clarificationNeeded"] = clarification_needed
                    if clarification_needed:
                        for msg in messages:
                            if hasattr(msg, "content") and isinstance(msg.content, str):
                                step_info["details"]["clarificationReason"] = msg.content.replace("CLARIFICATION_NEEDED:", "").strip()
                                break
                    
                    # Capture conversation context if available
                    for msg in messages:
                        if hasattr(msg, "content") and isinstance(msg.content, str) and "CONVERSATION CONTEXT:" in msg.content:
                            step_info["details"]["conversationContext"] = msg.content
                            break
                except Exception as e:
                    print(f"[AgentManager] Error extracting clarification info: {e}")
                    pass

            debug_steps.append(step_info)

        # Add memory/conversation history step
        memory_step = {
            "step": "Memory_System",
            "status": "completed",
            "details": {
                "conversationHistory": f"Retrieved {len(conversation_history)} messages from LangChain memory",
                "memoryWorking": len(conversation_history) > 0,
                "conversationContext": [f"{msg.__class__.__name__}: {msg.content[:100]}..." for msg in conversation_history[-3:]] if conversation_history else [],
                "memoryType": "ConversationBufferMemory"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        debug_steps.append(memory_step)

        print(f"[AgentManager] Total debug steps: {len(debug_steps)}")
        for i, step in enumerate(debug_steps):
            print(f"[AgentManager] Step {i}: {step['step']} - SQL: {'Yes' if step['details'].get('generatedSQL') else 'No'}")

        # Add the final result to memory for future conversations
        self.memory.chat_memory.add_ai_message(final_result)

        # Collect and display agent thoughts
        agent_thoughts = self._collect_agent_thoughts(results)
        if agent_thoughts:
            print(f"\n{'='*80}")
            print(f"🧠 AGENT THOUGHTS SUMMARY")
            print(f"{'='*80}")
            print(agent_thoughts)
            print(f"{'='*80}\n")

        # Collect decision traces
        decision_traces = self._collect_decision_traces(results)
        if decision_traces:
            print(f"\n{'='*80}")
            print(f"🔍 DECISION TRANSPARENCY TRACES")
            print(f"{'='*80}")
            for trace in decision_traces:
                print(f"\n--- {trace.get('agent', 'Unknown')} DECISION TRACE ---")
                print(f"Question: {trace.get('question', 'N/A')}")
                print(f"Tables Selected: {trace.get('tables_selected', trace.get('extracted_intent', {}).get('tables', []))}")
                print(f"Columns Selected: {trace.get('columns_selected', trace.get('extracted_intent', {}).get('columns', []))}")
                print(f"Filters Built: {trace.get('filters_built', trace.get('extracted_intent', {}).get('filters', []))}")
                print(f"Confidence Scores: {trace.get('confidence_scores', {})}")
                print(f"Signals Used: {trace.get('signals_used', trace.get('clarity_signals', []))}")
            print(f"{'='*80}\n")

        return {
            "final_result": final_result,
            "cleaned_query": final_sql,
            "raw_result_set": raw_result_set,
            "ba_summary": ba_summary,
            "agent_thoughts": agent_thoughts,
            "decision_traces": decision_traces,
            "debug": {
                "steps": debug_steps
            }
        }

    def process_conversational_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a query using enhanced conversational flow with human-like dialogue."""
        try:
            # Update processing status
            self.update_processing_status("Initializing", 0, "Starting conversational query processing")
            
            # Get conversation history
            conversation_history = self._get_conversation_history(state.get("conversation_id"))
            
            # Add conversation history to state
            state["conversation_history"] = conversation_history
            
            # Lazy import to avoid circular dependency
            if self.conversational_integration is None:
                from .conversational_integration import ConversationalIntegration
                self.conversational_integration = ConversationalIntegration(
                    db_util=self.db_util,
                    checkpoint=self.checkpoint,
                    template=self.template,
                    chatbot_db_util=self.chatbot_db_util,
                    chatbot_id=self.chatbot_id
                )
            
            # Process through enhanced conversational flow
            result = self.conversational_integration.process_query(state)
            
            # Update processing status
            self.update_processing_status("Completed", 100, "Conversational query processing completed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing conversational query: {e}")
            self.update_processing_status("Error", 0, f"Conversational query processing failed: {e}")
            raise QueryGenerationException(f"Conversational query processing failed: {e}")

    def _get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for the given conversation ID."""
        try:
            if not self.chatbot_db_util or not conversation_id:
                return []
            
            # Load conversation history using memory manager
            conversation_history = self.memory_manager.load_conversation_history(conversation_id)
            return conversation_history
            
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}")
            return []
    
    def _collect_agent_thoughts(self, results: List[Dict]) -> str:
        """Collect and format agent thoughts from workflow results."""
        thoughts = []
        
        # Look for agent_thoughts in each step's result
        for step in results:
            step_name = step.get("step", "")
            step_result = step.get("result", {})
            
            # Check if this step has agent thoughts
            if isinstance(step_result, dict) and "agent_thoughts" in step_result:
                agent_thoughts = step_result["agent_thoughts"]
                if agent_thoughts:
                    thoughts.append(f"\n--- {step_name} THOUGHTS ---")
                    thoughts.append(agent_thoughts)
                    thoughts.append("")
        
        return "\n".join(thoughts) if thoughts else ""
    
    def _collect_decision_traces(self, results: List[Dict]) -> List[Dict]:
        """Collect structured decision traces from workflow results."""
        traces = []
        
        # Look for decision_trace in each step's result
        for step in results:
            step_name = step.get("step", "")
            step_result = step.get("result", {})
            
            # Check if this step has decision trace
            if isinstance(step_result, dict) and "decision_trace" in step_result:
                decision_trace = step_result["decision_trace"]
                if decision_trace:
                    traces.append(decision_trace)
        
        return traces
