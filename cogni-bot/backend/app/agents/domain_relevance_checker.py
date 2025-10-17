import json
from typing import Optional, Dict, List, Any
from langchain_core.messages import SystemMessage
from langchain_core.language_models import BaseLanguageModel
from app.repositories.chatbot_db_util import ChatbotDbUtil
# from .conversation_aware_domain_checker import ConversationAwareDomainChecker  # Deleted agent


class DomainRelevanceCheckerAgent:
    def __init__(self, llm: BaseLanguageModel, chatbot_db_util: Optional[ChatbotDbUtil] = None):
        self.llm = llm
        self.chatbot_db_util = chatbot_db_util
        
        # Initialize conversation-aware domain checker
        self.conversation_aware_checker = ConversationAwareDomainChecker(llm, chatbot_db_util)

    def _extract_domain_from_schema(self, semantic_schema: dict, chatbot_db_util, chatbot_id: str) -> str:
        """Return explicit chatbot domain if configured; otherwise use LLM to infer domain."""
        try:
            bot_row = chatbot_db_util.get_chatbot(chatbot_id)
            explicit_domain = (bot_row or {}).get('domain') if bot_row else None
            if explicit_domain and isinstance(explicit_domain, str) and explicit_domain.strip():
                return explicit_domain.strip().lower()
            
            # Use LLM to infer domain from schema
            return self._infer_domain_with_llm(semantic_schema)
        except Exception as e:
            print(f"[Domain_Relevance_Checker] Error extracting domain: {e}")
            return "general"

    def _infer_domain_with_llm(self, semantic_schema: dict) -> str:
        """Use the LLM to intelligently infer the business domain from the schema context."""
        try:
            tables = semantic_schema.get('tables', {}) or {}
            
            # Build comprehensive schema context for LLM analysis
            schema_context = []
            for table_name, table_info in tables.items():
                columns = table_info.get('columns', {}) or {}
                column_details = []
                
                for col_name, col_info in columns.items():
                    col_type = col_info.get('type', 'unknown')
                    col_desc = col_info.get('description', '')
                    column_details.append(f"{col_name} ({col_type})" + (f" - {col_desc}" if col_desc else ""))
                
                schema_context.append(f"Table: {table_name}\nColumns: {', '.join(column_details)}")
            
            # Create comprehensive prompt for domain inference
            prompt = f"""You are an expert database domain classifier. Analyze the following database schema and determine the most appropriate business domain.

Database Schema:
{chr(10).join(schema_context[:20])}  # Limit to first 20 tables for context

Based on the table names, column names, data types, and descriptions, identify the primary business domain this database serves.

Consider these aspects:
1. What industry or business sector does this data represent?
2. What type of operations or processes are being tracked?
3. What kind of users would typically work with this data?
4. What business questions would this database answer?

Respond with a single, clear domain name that best describes this database's purpose. Examples: healthcare, finance, ecommerce, education, manufacturing, logistics, human_resources, sales, marketing, customer_support, general, etc.

If the database serves multiple domains or is too generic, respond with "general".

Domain:"""

            # DEBUG: Print the exact prompt for domain inference
            try:
                print("[Domain_Relevance_Checker] Domain inference prompt:\n" + prompt)
            except Exception:
                pass
            response = self.llm.invoke(prompt)
            inferred_domain = response.content.strip().lower() if hasattr(response, 'content') else str(response).strip().lower()
            
            # Clean up the response to get a valid domain name
            inferred_domain = inferred_domain.replace(' ', '_').replace('-', '_')
            
            print(f"[Domain_Relevance_Checker] LLM inferred domain: {inferred_domain}")
            return inferred_domain
            
        except Exception as e:
            print(f"[Domain_Relevance_Checker] LLM domain inference failed: {e}")
            return 'general'

    def _check_relevance_with_llm(self, question: str, domain: str, semantic_schema: dict) -> bool:
        """Use LLM to intelligently determine if question is relevant to the domain and database."""
        try:
            # Build context about the database for better relevance checking
            tables = semantic_schema.get('tables', {}) or {}
            table_names = list(tables.keys())[:10]  # Sample of table names
            
            prompt = f"""You are an expert domain relevance analyzer. Determine if the given question is relevant to the specified database domain and schema.

Question: "{question}"
Database Domain: {domain}
Available Tables: {', '.join(table_names)}

Analyze the relevance by considering:
1. Does the question ask about data that would logically exist in a {domain} database?
2. Are the concepts, entities, or processes mentioned typical of {domain} operations?
3. Would a {domain} professional be able to answer this question using their database?
4. Do the table names suggest this database could contain the data needed to answer the question?
5. Is the question asking about business processes or data that aligns with {domain} workflows?

Be intelligent and consider:
- Synonyms and related terms (e.g., "customer" and "client" are similar)
- Business context (e.g., "sales" questions are relevant to both ecommerce and sales domains)
- Data relationships (e.g., "employee performance" could be relevant to HR, management, or general business domains)
- The specific table names available in the database

If the question is clearly irrelevant to the domain or the available data, respond with NO.
If the question could reasonably be answered using this {domain} database, respond with YES.
If you're uncertain, lean towards YES to avoid blocking potentially valid questions.

Answer only: YES or NO"""

            # DEBUG: Print the exact prompt for relevance check
            try:
                print("[Domain_Relevance_Checker] Relevance check prompt:\n" + prompt)
            except Exception:
                pass
            response = self.llm.invoke(prompt)
            result = response.content.strip().upper() if hasattr(response, 'content') else str(response).strip().upper()

            is_relevant = "YES" in result
            print(f"[Domain_Relevance_Checker] LLM relevance check: {result} -> {is_relevant}")

            # Heuristic safety net: if LLM said NO but the question strongly matches schema tokens, allow it
            if not is_relevant:
                try:
                    import re as _re
                    q_tokens = set(_re.findall(r"[a-zA-Z0-9_]{3,}", (question or "").lower()))
                    table_names = set([t.lower() for t in (semantic_schema.get('tables', {}) or {}).keys()])
                    # Expand schema tokens with common finance/HR keywords from column hints
                    column_tokens = set()
                    for t_name, t in (semantic_schema.get('tables', {}) or {}).items():
                        for c_name in (t.get('columns', {}) or {}).keys():
                            column_tokens.add(str(c_name).lower())
                    schema_tokens = table_names.union(column_tokens)
                    # Common domain-neutral tokens that indicate data relevance
                    common = {"employee", "employees", "transaction", "transactions", "expense", "expenses", "rule", "rules"}
                    schema_tokens = schema_tokens.union(common)
                    overlap = q_tokens.intersection(schema_tokens)
                    if overlap:
                        print(f"[Domain_Relevance_Checker] Heuristic override to YES due to token overlap: {sorted(list(overlap))[:10]}")
                        return True
                except Exception:
                    pass

            return is_relevant
            
        except Exception as e:
            print(f"[Domain_Relevance_Checker] LLM relevance check failed: {e}")
            return True  # Default to relevant if LLM fails

    def run(self, state: dict, chatbot_id: str, chatbot_db_util) -> dict:
        """Check if the question is relevant to the configured database domain using conversation-aware LLM intelligence."""
        print(f"[Domain_Relevance_Checker] Starting conversation-aware domain relevance check for chatbot {chatbot_id}")
        
        # Get the user's question
        question = ""
        for message in reversed(state.get("messages", [])):
            if hasattr(message, 'content'):
                content = message.content
            else:
                content = str(message)
            
            # Skip system messages
            if content.startswith("INTENT:") or content.startswith("CLIPPED:"):
                continue
                
            # Look for human messages
            if hasattr(message, '__class__') and message.__class__.__name__ == "HumanMessage":
                question = content
                break
            elif not content.startswith("INTENT:") and not content.startswith("CLIPPED:") and content.strip():
                question = content
                break
        
        if not question:
            print("[Domain_Relevance_Checker] No question found")
            return state
        
        print(f"[Domain_Relevance_Checker] Question: {question}")
        
        try:
            # Get semantic schema to determine domain
            semantic_schema_json = chatbot_db_util.get_semantic_schema(chatbot_id)
            if not semantic_schema_json:
                print("[Domain_Relevance_Checker] No semantic schema found, allowing question to proceed")
                state["domain_check_failed"] = False
                return state
            
            semantic_schema = json.loads(semantic_schema_json)
            
            # Extract conversation history for context awareness
            conversation_history = self._extract_conversation_history(state)
            
            # Use conversation-aware domain checker
            relevance_result = self.conversation_aware_checker.check_domain_relevance_with_context(
                question, conversation_history, semantic_schema, chatbot_id
            )
            
            if relevance_result.get("is_follow_up", False):
                print(f"[Domain_Relevance_Checker] Detected follow-up response: {relevance_result['follow_up_type']}")
                print(f"[Domain_Relevance_Checker] Original question: {relevance_result.get('original_question', 'N/A')}")
                state["domain_check_failed"] = False
                state["is_follow_up"] = True
                state["follow_up_type"] = relevance_result.get('follow_up_type')
                state["original_question"] = relevance_result.get('original_question')
                return state
            elif relevance_result.get("is_relevant", False):
                print(f"[Domain_Relevance_Checker] Question is relevant to {relevance_result.get('domain', 'unknown')} domain, proceeding")
                state["domain_check_failed"] = False
                state["detected_domain"] = relevance_result.get('domain')
                return state
            else:
                print(f"[Domain_Relevance_Checker] Question is not relevant to {relevance_result.get('domain', 'unknown')} domain")
                error_message = self._generate_domain_error_message(question, relevance_result.get('domain', 'unknown'), semantic_schema)
                state["domain_check_failed"] = True
                state["domain_error_message"] = error_message
                state["messages"].append(SystemMessage(content=f"DOMAIN_CHECK_FAILED: {error_message}"))
                return state
                
        except Exception as e:
            print(f"[Domain_Relevance_Checker] Error during conversation-aware relevance check: {e}")
            # If check fails, proceed with the question to avoid blocking valid queries
            state["domain_check_failed"] = False
            return state

    def _extract_conversation_history(self, state: dict) -> List[Dict]:
        """Extract conversation history from state for context awareness."""
        try:
            conversation_history = []
            messages = state.get("messages", [])
            
            for message in messages:
                if hasattr(message, 'content'):
                    content = message.content
                else:
                    content = str(message)
                
                # Skip system messages
                if content.startswith("INTENT:") or content.startswith("CLIPPED:") or content.startswith("DOMAIN_CHECK_FAILED:"):
                    continue
                
                # Determine message role
                if hasattr(message, '__class__'):
                    if message.__class__.__name__ == "HumanMessage":
                        role = "user"
                    elif message.__class__.__name__ == "AIMessage":
                        role = "assistant"
                    else:
                        role = "system"
                else:
                    role = "user"  # Default to user
                
                conversation_history.append({
                    "role": role,
                    "content": content,
                    "message": content
                })
            
            return conversation_history
            
        except Exception as e:
            print(f"[Domain_Relevance_Checker] Error extracting conversation history: {e}")
            return []

    def _generate_domain_error_message(self, question: str, domain: str, semantic_schema: dict) -> str:
        """Generate a helpful error message using LLM when question is not relevant."""
        try:
            tables = semantic_schema.get('tables', {}) or {}
            table_names = list(tables.keys())[:10]
            
            prompt = f"""You are a helpful assistant that provides guidance when users ask questions that don't match the database domain.

Question asked: "{question}"
Database Domain: {domain}
Available Tables: {', '.join(table_names)}

Generate a helpful, friendly error message that:
1. Politely explains that the question doesn't match the {domain} domain
2. Suggests the types of questions that would be relevant for this {domain} database
3. Mentions some of the available tables to give context
4. Encourages the user to ask domain-appropriate questions

Keep the message concise (2-3 sentences) and helpful.

Error message:"""

            # DEBUG: Print the exact prompt for error message generation
            try:
                print("[Domain_Relevance_Checker] Error message prompt:\n" + prompt)
            except Exception:
                pass
            response = self.llm.invoke(prompt)
            error_message = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            
            # Fallback to a generic message if LLM fails
            if not error_message or len(error_message) < 10:
                error_message = f"This question doesn't seem relevant to the {domain} domain. Please ask questions about {domain} data, such as information related to the available tables: {', '.join(table_names[:5])}."
            
            return error_message
            
        except Exception as e:
            print(f"[Domain_Relevance_Checker] Error generating error message: {e}")
            return f"This question doesn't seem relevant to the {domain} domain. Please ask questions about {domain} data."
