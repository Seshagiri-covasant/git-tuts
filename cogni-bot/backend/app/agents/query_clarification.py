import json
import re
from typing import Optional, List, Dict
import logging
from langchain_core.messages import SystemMessage
from langchain_core.language_models import BaseLanguageModel
from app.repositories.chatbot_db_util import ChatbotDbUtil


class QueryClarificationAgent:
    def __init__(self, llm: BaseLanguageModel, chatbot_db_util: Optional[ChatbotDbUtil] = None):
        self.llm = llm
        self.chatbot_db_util = chatbot_db_util
        self.logger = logging.getLogger(__name__)

    def _build_knowledge_overview(self, knowledge_data: Dict[str, any]) -> str:
        """Build compact knowledge overview similar to Intent Picker."""
        tables: List[str] = []
        columns: List[str] = []
        synonyms_table = []
        synonyms_column = []

        for k, v in (knowledge_data or {}).items():
            if k.startswith("table:"):
                tables.append(k.split(":", 1)[1])
            elif k.startswith("column:"):
                columns.append(k.split(":", 1)[1])
            elif k.startswith("synonym:table:"):
                synonyms_table.append(f"{k.replace('synonym:table:','')} -> {', '.join(v)}")
            elif k.startswith("synonym:column:"):
                synonyms_column.append(f"{k.replace('synonym:column:','')} -> {', '.join(v)}")

        overview = "\n".join([
            "TABLES:", ", ".join(sorted(tables)) or "",
            "\nCOLUMNS:", ", ".join(sorted(columns)) or "",
            "\nTABLE SYNONYMS:", "\n".join(sorted(synonyms_table)) or "",
            "\nCOLUMN SYNONYMS:", "\n".join(sorted(synonyms_column)) or "",
        ])
        return overview

    def _detect_ambiguity_optimized(self, question: str, intent: dict, knowledge_overview: str) -> Dict:
        """Detect ambiguity using intent and compact knowledge overview."""
        try:
            prompt = f"""You are an expert SQL query ambiguity detector. Analyze the question against the identified intent and available database structure.

QUESTION: "{question}"

IDENTIFIED INTENT:
- Target Tables: {intent.get('tables', [])}
- Target Columns: {intent.get('columns', [])}
- Filters: {intent.get('filters', [])}
- Joins: {intent.get('joins', [])}
- Order By: {intent.get('order_by', [])}
- Date Range: {intent.get('date_range', 'None')}

AVAILABLE DATABASE STRUCTURE:
{knowledge_overview}

AMBIGUITY ANALYSIS:
Check for these specific issues:

1. **INCOMPLETE_SPECIFICATION**: 
   - Missing specific entity (which customer/product/record?)
   - Missing column details (what specific information?)
   - Example: "customer details" → which customer? what details?

2. **IMPLICIT_INTENT**:
   - Missing DISTINCT for "top X" queries
   - Missing ORDER BY for ranking queries
   - Missing GROUP BY for aggregation
   - Example: "top 5 medicines" → needs DISTINCT + ORDER BY

3. **VAGUE_REFERENCE**:
   - Unclear time references ("recent", "latest")
   - Ambiguous quantities ("few", "many")
   - Example: "recent orders" → how recent?

4. **MISSING_CRITERIA**:
   - No filtering when specific criteria expected
   - Example: "all products" → any category/status filters?

5. **UNCLEAR_AGGREGATION**:
   - Ambiguous grouping dimensions
   - Example: "total sales" → by what? (product, region, time?)

Respond in JSON format:
{{
    "is_ambiguous": true/false,
    "confidence": 0.0-1.0,
    "ambiguity_types": ["INCOMPLETE_SPECIFICATION", "IMPLICIT_INTENT"],
    "missing_details": {{
        "specific_entity": "which customer/product/etc",
        "required_columns": ["column1", "column2"],
        "missing_operations": ["DISTINCT", "ORDER BY", "GROUP BY"],
        "filtering_criteria": "time range, conditions, etc"
    }},
    "suggested_clarifications": [
        "Show me customer details for customer ID 12345",
        "List all customers with their contact information",
        "Find customers who made purchases recently"
    ]
}}"""

            # Print full prompt going to LLM (stdout + logger)
            msg_out = "[Query_Clarification] LLM PROMPT START\n" + prompt + "\n[Query_Clarification] LLM PROMPT END"
            try:
                print(msg_out)
            except Exception:
                pass
            try:
                # Sanitize for Windows cp1252 consoles to avoid UnicodeEncodeError
                safe_out = msg_out.encode('cp1252', errors='ignore').decode('cp1252')
                self.logger.info(safe_out)
            except Exception:
                pass

            response = self.llm.invoke(prompt)
            raw = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            # Print full raw response from LLM (stdout + logger)
            msg_in = "[Query_Clarification] LLM RESPONSE START\n" + raw + "\n[Query_Clarification] LLM RESPONSE END"
            try:
                print(msg_in)
            except Exception:
                pass
            try:
                safe_in = msg_in.encode('cp1252', errors='ignore').decode('cp1252')
                self.logger.info(safe_in)
            except Exception:
                pass

            # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
            cleaned = re.sub(r"^```(?:json|javascript|js|txt)?\s*", "", raw.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned.strip())

            # If still not clean JSON, try to extract the first JSON object/array
            if not (cleaned.strip().startswith("{") or cleaned.strip().startswith("[")):
                match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
                if match:
                    cleaned = match.group(1)

            try:
                ambiguity_data = json.loads(cleaned)
                print(f"[Query_Clarification] Ambiguity detection: {ambiguity_data}")
                return ambiguity_data
            except json.JSONDecodeError:
                print(f"[Query_Clarification] Failed to parse LLM response: {raw}")
                return {"is_ambiguous": False, "ambiguity_types": [], "missing_details": {}, "confidence": 0.0, "suggested_clarifications": []}
                
        except Exception as e:
            print(f"[Query_Clarification] Error detecting ambiguity: {e}")
            return {"is_ambiguous": False, "ambiguity_types": [], "missing_details": {}, "confidence": 0.0, "suggested_clarifications": []}

    def _create_clarification_response(self, question: str, suggestions: List[str], ambiguity_data: Dict) -> str:
        """Create a helpful clarification response with suggestions."""
        try:
            ambiguity_types = ambiguity_data.get('ambiguity_types', [])
            
            response_parts = [
                "I need some clarification to provide you with the most accurate results. Your question seems to be missing some specific details:"
            ]
            
            # Add specific issues found
            if 'INCOMPLETE_SPECIFICATION' in ambiguity_types:
                response_parts.append("• Which specific item are you looking for? (e.g., which customer, product, etc.)")
            
            if 'IMPLICIT_INTENT' in ambiguity_types:
                response_parts.append("• What specific operations do you need? (e.g., distinct values, sorting, grouping)")
            
            if 'VAGUE_REFERENCE' in ambiguity_types:
                response_parts.append("• Can you be more specific about time ranges or criteria?")
            
            if 'MISSING_CRITERIA' in ambiguity_types:
                response_parts.append("• Do you need any specific filters or conditions?")
            
            if 'UNCLEAR_AGGREGATION' in ambiguity_types:
                response_parts.append("• What grouping or aggregation do you need?")
            
            response_parts.append("\nHere are some specific questions you could ask instead:")
            
            for i, suggestion in enumerate(suggestions, 1):
                response_parts.append(f"{i}. {suggestion}")
            
            response_parts.append("\nPlease select one of these options or rephrase your question with more specific details.")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            print(f"[Query_Clarification] Error creating response: {e}")
            return f"I need more specific details to answer your question. Could you please clarify what specific information you're looking for from the database?"

    def run(self, state: dict, chatbot_id: str, chatbot_db_util) -> dict:
        """Check if the question needs clarification and provide suggestions."""
        print(f"[Query_Clarification] Starting query clarification check for chatbot {chatbot_id}")
        
        # Get the user's question
        question = ""
        for message in reversed(state.get("messages", [])):
            if hasattr(message, 'content'):
                content = message.content
            else:
                content = str(message)
            
            # Skip system messages
            if content.startswith("INTENT:") or content.startswith("CLIPPED:") or content.startswith("DOMAIN_CHECK_FAILED:"):
                continue
                
            # Look for human messages
            if hasattr(message, '__class__') and message.__class__.__name__ == "HumanMessage":
                question = content
                break
            elif not content.startswith("INTENT:") and not content.startswith("CLIPPED:") and not content.startswith("DOMAIN_CHECK_FAILED:") and content.strip():
                question = content
                break
        
        if not question:
            print("[Query_Clarification] No question found")
            return state
        
        print(f"[Query_Clarification] Question: {question}")
        
        try:
            # Get intent from state (should be available from Intent Picker)
            intent = {}
            for msg in reversed(state.get("messages", [])):
                content_str = None
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str):
                        content_str = c
                elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                    content_str = getattr(msg, "content")
                if content_str and content_str.startswith("INTENT:"):
                    try:
                        intent = json.loads(content_str[7:])
                    except Exception:
                        intent = {}
                    break
            
            if not intent:
                print("[Query_Clarification] No intent found, proceeding without clarification")
                state["clarification_needed"] = False
                return state
            
            # Load knowledge cache for overview
            cache = chatbot_db_util.get_semantic_knowledge_cache(chatbot_id)
            knowledge_data = cache.get("knowledge_data") if cache else {}
            
            # Build compact overview
            knowledge_overview = self._build_knowledge_overview(knowledge_data)
            
            # Detect ambiguity
            ambiguity_data = self._detect_ambiguity_optimized(question, intent, knowledge_overview)
            
            # Only ask for clarification if confidence is high and ambiguity is significant
            confidence = ambiguity_data.get('confidence', 0.0)
            is_ambiguous = ambiguity_data.get('is_ambiguous', False)
            
            if is_ambiguous and confidence > 0.7:
                print(f"[Query_Clarification] Question is ambiguous (confidence: {confidence})")
                
                # Get suggestions from LLM response or generate fallback
                suggestions = ambiguity_data.get('suggested_clarifications', [])
                if not suggestions or len(suggestions) < 3:
                    # Generate fallback suggestions based on intent
                    target_tables = intent.get('tables', [])
                    suggestions = [
                        f"Show me all records from {target_tables[0] if target_tables else 'the main table'}",
                        f"Give me a summary of {target_tables[1] if len(target_tables) > 1 else 'data'} with specific criteria",
                        f"List the top 10 items from {target_tables[0] if target_tables else 'the database'} with details"
                    ]
                
                # Create clarification response
                clarification_response = self._create_clarification_response(question, suggestions, ambiguity_data)
                
                # Add clarification needed marker
                state["clarification_needed"] = True
                state["clarification_suggestions"] = suggestions
                state["original_question"] = question
                state["messages"].append(SystemMessage(content=f"CLARIFICATION_NEEDED: {clarification_response}"))
                
                return state
            else:
                print(f"[Query_Clarification] Question is clear enough (confidence: {confidence}), proceeding")
                state["clarification_needed"] = False
                return state
                
        except Exception as e:
            print(f"[Query_Clarification] Error during clarification check: {e}")
            # If check fails, proceed with the question
            state["clarification_needed"] = False
            return state