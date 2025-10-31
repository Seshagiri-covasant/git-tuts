#!/usr/bin/env python3
"""
Human Approval Agent for Intent Validation (Dialogue Manager)
"""

import re
from typing import Any, Dict, List
from langchain_core.language_models import BaseLanguageModel
from app.schemas.followups import FollowUpQuestion
from collections import defaultdict

# spaCy import with fallback
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("[HumanApprovalAgent] spaCy not available, will use regex fallback")

class HumanApprovalAgent:
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
        self.nlp = None
        
        # Load spaCy model with error handling
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                print("[HumanApprovalAgent] spaCy model loaded successfully")
            except OSError:
                print("[HumanApprovalAgent] spaCy model 'en_core_web_sm' not found. Attempting to download...")
                try:
                    from spacy.cli import download
                    download("en_core_web_sm")
                    self.nlp = spacy.load("en_core_web_sm")
                    print("[HumanApprovalAgent] spaCy model downloaded and loaded successfully")
                except Exception as e:
                    print(f"[HumanApprovalAgent] Failed to download spaCy model: {e}")
                    print("[HumanApprovalAgent] Falling back to regex-based extraction")
                    self.nlp = None
            except Exception as e:
                print(f"[HumanApprovalAgent] Error loading spaCy model: {e}")
                print("[HumanApprovalAgent] Falling back to regex-based extraction")
                self.nlp = None
        else:
            print("[HumanApprovalAgent] spaCy not available, using regex-based extraction")
        
    def _find_competing_columns(self, user_question: str, knowledge_data: Dict, intent: Dict = None) -> List[Dict]:
        """
        Finds ambiguity ONLY in the potential ATTRIBUTES of a query, not the subject.
        
        If intent picker has high confidence and already selected columns, trust that decision
        and skip ambiguity detection.
        """
        # Trust intent picker's high-confidence decision
        if intent:
            confidence = intent.get('confidence', {}).get('overall', 0.0)
            selected_columns = intent.get('columns', [])
            
            # If intent picker has high confidence (>= 0.9) and already selected specific columns,
            # trust that decision and skip ambiguity detection
            if confidence >= 0.9 and selected_columns:
                print(f"[HumanApprovalAgent] Intent picker has high confidence ({confidence}) and selected columns: {selected_columns}. Trusting decision and skipping ambiguity check.")
                return []
        
        # Check if this is a relationship question first
        if self._is_relationship_question(user_question):
            print(f"[HumanApprovalAgent] Question is about relationships, skipping ambiguity check")
            return []
        
        # This now gets a much smaller, more relevant list of terms to check.
        potential_attributes = self._extract_key_terms_from_question(user_question)
        if not potential_attributes:
            return []

        schema = knowledge_data.get('schema', {})
        all_tables = schema.get('tables', {})
        
        # Check each potential attribute for ambiguity.
        for attribute in potential_attributes:
            candidate_columns = []
            for table_name, table_data in all_tables.items():
                if not isinstance(table_data, dict): continue
                for col_name, col_data in table_data.get('columns', {}).items():
                    if not isinstance(col_data, dict): continue
                    
                    context_text = (
                        f"{col_name} {col_data.get('description', '')} "
                        f"{' '.join(col_data.get('business_terms', []))}"
                    ).lower()
                    
                    # Check if the column's context is a plausible match for the attribute.
                    if attribute in context_text.replace('_', ' ').lower():
                        candidate_columns.append({
                            "name": col_name,
                            "description": col_data.get('description', 'No description provided.'),
                            "table_name": table_name
                        })
            
            # If this specific attribute maps to more than one column, we have found a real ambiguity.
            if len(candidate_columns) > 1:
                print(f"[HumanApprovalAgent] Found competing columns for attribute '{attribute}': {[col['name'] for col in candidate_columns]}")
                return candidate_columns
        
        return []
    
    
    def _is_question_specific_enough(self, question: str, term: str, columns: List[Dict]) -> bool:
        """
        Check if the user's question provides enough context to disambiguate between columns.
        """
        question_lower = question.lower()
        
        # If the question mentions specific column names, it's specific enough
        for col in columns:
            col_name_lower = col['name'].lower().replace('_', ' ')
            if col_name_lower in question_lower:
                return True
        
        # Check if the question contains distinguishing terms that would help choose between columns
        # We need to find terms that are specific to individual columns, not common to all
        distinguishing_terms = []
        for col in columns:
            description = col.get('description', '').lower()
            business_terms = col.get('business_terms', [])
            
            # Extract distinguishing terms (longer, more specific terms)
            for term_word in description.split():
                if len(term_word) > 4 and term_word not in ['the', 'for', 'and', 'with', 'from']:
                    distinguishing_terms.append(term_word)
            

        
        # Check if the question contains any distinguishing terms
        for dist_term in distinguishing_terms:
            if dist_term in question_lower:
                print(f"[HumanApprovalAgent] Found distinguishing term '{dist_term}' in question")
                return True
        
        # Special case: if the question is very generic (like "what is the risk score"),
        # it's not specific enough even if it contains some terms
        generic_patterns = [
            "what is the", "show me the", "give me the", "what are the",
            "list the", "find the", "get the"
        ]
        
        for pattern in generic_patterns:
            if pattern in question_lower and len(columns) > 2:
                # Generic question with many competing columns = not specific enough
                return False
        
        # Special case: if the question is asking about relationships or analysis (like "are X linked to Y"),
        # it's specific enough even with multiple columns
        relationship_patterns = [
            "are", "linked to", "related to", "connected to", "associated with",
            "correlation", "relationship", "analysis", "compare"
        ]
        
        for pattern in relationship_patterns:
            if pattern in question_lower:
                print(f"[HumanApprovalAgent] Question contains relationship pattern '{pattern}', considering it specific enough")
                return True
        
        # If we have multiple columns and the question doesn't contain specific distinguishing terms,
        # it's not specific enough
        if len(columns) > 2:
            return False
        
        return False
    
    def _are_columns_competing(self, columns: List[Dict]) -> bool:
        """
        Check if columns are genuinely competing (serving the same purpose) 
        rather than complementary (serving different purposes).
        """
        if len(columns) < 2:
            return False
        
        # Extract key concepts from each column
        column_concepts = []
        for col in columns:
            concepts = set()
            name_words = col['name'].lower().replace('_', ' ').split()
            description_words = col.get('description', '').lower().split()
            business_terms = [term.lower() for term in col.get('business_terms', [])]
            
            concepts.update(name_words)
            concepts.update(description_words)
            concepts.update(business_terms)
            column_concepts.append(concepts)
        
        # Check if columns share significant overlap in concepts
        # If they do, they're competing; if not, they're complementary
        for i in range(len(column_concepts)):
            for j in range(i + 1, len(column_concepts)):
                overlap = column_concepts[i] & column_concepts[j]
                # If more than 50% of concepts overlap, they're competing
                if len(overlap) > len(column_concepts[i]) * 0.5:
                    return True
        
        return False
    
    def _extract_key_terms_from_question(self, question: str) -> List[str]:
        """
        Extracts potential ATTRIBUTES from a user question. This is more targeted.
        It looks for nouns that follow descriptive verbs or are part of compound nouns.
        Falls back to regex if spaCy is not available.
        """
        if self.nlp is not None:
            return self._spacy_extract_attributes(question)
        else:
            return self._regex_extract_attributes(question)
    
    def _spacy_extract_attributes(self, question: str) -> List[str]:
        """
        Extracts potential ATTRIBUTES from a user question. This is more targeted.
        It looks for nouns that follow descriptive verbs or are part of compound nouns.
        """
        doc = self.nlp(question.lower())
        attributes = set()

        # Heuristic: Attributes are often compound nouns or nouns following verbs like "show me the..."
        for chunk in doc.noun_chunks:
            # A simple way to check if it's a primary subject vs. an attribute
            # is to see if it's a multi-word phrase or a common metric word.
            if ' ' in chunk.text or any(w in chunk.text for w in ['score', 'amount', 'date', 'name', 'id', 'category', 'type', 'flag']):
                 attributes.add(chunk.text)

        # Add single nouns that look like attributes
        for token in doc:
            if token.pos_ == "NOUN" and any(w in token.text for w in ['score', 'amount', 'date', 'name', 'id', 'category', 'type', 'flag']):
                attributes.add(token.text)
                
        final_terms = list(attributes)
        print(f"[HumanApprovalAgent][spaCy] Extracted potential ATTRIBUTES: {final_terms}")
        return final_terms
    
    def _regex_extract_attributes(self, question: str) -> List[str]:
        """
        Fallback regex-based attribute extraction.
        """
        potential_phrases = re.findall(r'\b(?:[a-z_][a-z\'-_]+(?:\s+|$))+', question.lower())
        stop_words = {'the', 'a', 'an', 'is', 'are', 'what', 'which', 'show', 'me', 'find', 'get', 'list', 'for', 'of', 'with', 'and', 'by'}
        
        # Filter for attributes (terms containing common attribute words)
        attributes = []
        for phrase in potential_phrases:
            phrase = phrase.strip()
            if (phrase not in stop_words and 
                len(phrase) > 2 and 
                any(w in phrase for w in ['score', 'amount', 'date', 'name', 'id', 'category', 'type', 'flag'])):
                attributes.append(phrase)
        
        print(f"[HumanApprovalAgent][Regex] Extracted potential ATTRIBUTES: {attributes}")
        return list(set(attributes))

    def _build_business_summary(self, intent: Dict) -> str:
        """Creates a plain English summary of the intent."""
        tables = intent.get('tables', [])
        columns = intent.get('columns', [])
        filters = intent.get('filters', [])
        if not tables: return "process your request"
        
        table_desc = f"the {', '.join(tables)} data"
        column_desc = "all relevant information"
        if columns:
            column_desc = f"the following information: {', '.join([c.replace('_', ' ') for c in columns])}"
        filter_desc = f" where {' and '.join(filters)}" if filters else ""
        
        return f"retrieve {column_desc} from {table_desc}{filter_desc}"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main logic for the Dialogue Manager. It verifies the proposed intent and
        chooses one of three paths: Clarify, Confirm, or Proceed Automatically.
        """
        try:
            intent = state.get('intent', {})
            knowledge_data = state.get('knowledge_data', {})
            user_question = state.get('user_question', '')
            
            # --- DUTY 1: Proactively and Independently Check for Ambiguity ---
            # This now correctly ignores relationship questions and focuses on attributes.
            # Pass intent so we can trust high-confidence decisions from intent picker
            competing_columns = self._find_competing_columns(user_question, knowledge_data, intent)
            
            if competing_columns:
                # --- ACTION A: Ambiguity Found -> Force Clarification ---
                print(f"[HumanApprovalAgent] Ambiguity detected. Pausing for user clarification.")
                options = [{'id': c['name'], 'display_name': c['name'].replace('_', ' ').title(), 'description': c['description']} for c in competing_columns]
                approval_request = {
                    'source_agent': 'SQL_Agent',
                    'clarification_details': {
                        'type': 'CHOICE_SELECTION',
                        'question_text': f"To get the right data for '{user_question}', I need a bit more detail. Which of these options best matches what you're looking for?",
                        'options': options
                    }
                }
                
                print(f"[HumanApprovalAgent] Asking for clarification: {approval_request['clarification_details']['question_text']}")
                print(f"[HumanApprovalAgent] Available options: {[opt['display_name'] for opt in options]}")
                follow_up = FollowUpQuestion(
                    question=approval_request['clarification_details']['question_text'],
                    answer_options=[opt['display_name'] for opt in options],
                    multiple_selection=False,
                ).model_dump()
                return {**state, 'human_approval_needed': True, 'approval_request': approval_request, 'follow_up_questions': [follow_up], '__interrupt__': True}

            # --- DUTY 2: If No Ambiguity, Decide Whether to Proceed Automatically or Ask for Confirmation ---
            confidence = intent.get('confidence', {}).get('overall', 0.0)
            
            # Enhanced complexity detection that works with adaptive intent picker
            is_complex_query = self._is_truly_complex_query(intent, user_question)
            
            # Check if this is a relationship question (should be handled automatically)
            is_relationship_question = self._is_relationship_question(user_question)
            
            # THE "ADAPTIVE FAST LANE" LOGIC:
            if confidence >= 0.90 and not is_complex_query:
                # --- ACTION B: High Confidence & Not Complex -> PROCEED AUTOMATICALLY ---
                print(f"[HumanApprovalAgent] Intent has high confidence ({confidence}) and is not complex. Proceeding automatically.")
                return {
                    **state, 
                    'human_approval_needed': False, 
                    'intent_approved': True
                }
            elif is_relationship_question and confidence >= 0.85:
                # --- ACTION B2: Relationship questions with good confidence -> PROCEED AUTOMATICALLY ---
                print(f"[HumanApprovalAgent] Relationship question with good confidence ({confidence}). Proceeding automatically.")
                return {
                    **state, 
                    'human_approval_needed': False, 
                    'intent_approved': True
                }
            else:
                # --- ACTION C: Intent needs confirmation -> Ask for Confirmation ---
                print(f"[HumanApprovalAgent] Intent requires user confirmation (Is Complex: {is_complex_query}, Is Relationship: {is_relationship_question}, Confidence: {confidence}). Pausing.")
                summary = self._build_business_summary(intent)
            approval_request = {
                    'source_agent': 'SQL_Agent',
                    'clarification_details': {
                        'type': 'CONFIRMATION',
                        'question_text': f"Just to confirm, you'd like me to {summary}. Is that correct?",
                        'options': [{'id': 'confirm', 'display_name': 'Yes, proceed'}, {'id': 'deny', 'display_name': 'No, that is incorrect'}]
                    }
                }
                
            print(f"[HumanApprovalAgent] Asking for confirmation: {approval_request['clarification_details']['question_text']}")
            print(f"[HumanApprovalAgent] Available options: {[opt['display_name'] for opt in approval_request['clarification_details']['options']]}")
            follow_up = FollowUpQuestion(
                question=approval_request['clarification_details']['question_text'],
                answer_options=[opt['display_name'] for opt in approval_request['clarification_details']['options']],
                multiple_selection=False,
            ).model_dump()
            return {**state, 'human_approval_needed': True, 'approval_request': approval_request, 'follow_up_questions': [follow_up], '__interrupt__': True}
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error during approval check: {e}")
            return {**state, 'human_approval_needed': False, 'intent_approved': True} # Fail open

    def _is_truly_complex_query(self, intent: Dict, user_question: str) -> bool:
        """
        Enhanced complexity detection that works with adaptive intent picker.
        Only considers queries truly complex if they have multiple complex features.
        """
        try:
            # Basic complexity indicators
            has_multiple_tables = len(intent.get('tables', [])) > 1
            has_filters = len(intent.get('filters', [])) > 0
            has_aggregations = len(intent.get('aggregations', [])) > 0
            has_joins = len(intent.get('joins', [])) > 0
            
            # Count complexity features
            complexity_features = sum([
                has_multiple_tables,
                has_aggregations,
                has_joins
            ])
            
            # Simple filters (like risk score thresholds) don't make a query complex
            # Only consider it complex if there are multiple complex features
            is_complex = complexity_features >= 2
            
            # Special case: single table with simple filters should not be complex
            if not has_multiple_tables and not has_aggregations and not has_joins:
                is_complex = False
            
            print(f"[HumanApprovalAgent] Complexity analysis: Tables={has_multiple_tables}, Filters={has_filters}, Aggregations={has_aggregations}, Joins={has_joins}, Features={complexity_features}, IsComplex={is_complex}")
            
            return is_complex
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error in complexity analysis: {e}")
            return False

    def _is_relationship_question(self, user_question: str) -> bool:
        """
        Check if the question is asking about relationships between entities.
        These should generally be handled automatically with good confidence.
        """
        try:
            question_lower = user_question.lower()
            
            # Relationship question indicators
            relationship_indicators = [
                'linked to', 'related to', 'associated with', 'connected to',
                'relationship between', 'correlation between', 'connection between',
                'how are', 'what is the relationship', 'what is the connection',
                'linked', 'associated', 'connected', 'correlated'
            ]
            
            # Check for relationship indicators
            has_relationship_indicator = any(indicator in question_lower for indicator in relationship_indicators)
            
            # Check for question patterns that suggest relationships
            has_relationship_pattern = any([
                'linked to certain' in question_lower,
                'related to specific' in question_lower,
                'associated with particular' in question_lower,
                'connected to different' in question_lower
            ])
            
            is_relationship = has_relationship_indicator or has_relationship_pattern
            
            print(f"[HumanApprovalAgent] Relationship analysis: HasIndicator={has_relationship_indicator}, HasPattern={has_relationship_pattern}, IsRelationship={is_relationship}")
            
            return is_relationship
            
        except Exception as e:
            print(f"[HumanApprovalAgent] Error in relationship analysis: {e}")
            return False
    
    def handle_human_response(self, state: Dict[str, Any], human_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle human response to approval request.
        """
        try:
            response_type = human_response.get('type', 'approval')
            response_data = human_response.get('response_data', {})
            
            print(f"[HumanApprovalAgent] Handling human response: {response_type}")
            print(f"[HumanApprovalAgent] Response data: {response_data}")
            
            if response_type == 'choice_selection':
                # User selected from multiple options
                selected_option = response_data.get('selected_option')
                if selected_option:
                    # Update the intent with the selected column
                    intent = state.get('intent', {}).copy()
                    intent['columns'] = [selected_option]
                    intent['clarification_resolved'] = True
                    
                return {
                    **state,
                        'intent': intent,
                    'human_approval_needed': False,
                    'intent_approved': True,
                        'clarification_needed': False,
                    'human_response': human_response
                }
            
            elif response_type == 'confirmation':
                # User confirmed or denied the summary
                confirmed = response_data.get('confirmed', False)
                if confirmed:
                    return {
                        **state,
                        'human_approval_needed': False,
                        'intent_approved': True,
                        'clarification_needed': False,
                        'human_response': human_response
                    }
                else:
                    # User denied - ask what was incorrect.
                    denial_message = "My apologies for the misunderstanding. Could you please tell me what was incorrect or what you would like to change?"
                    
                    # We need to re-interrupt the flow to ask this new question.
                    approval_request = {
                        'source_agent': 'SQL_Agent',
                        'clarification_details': {
                            'type': 'GENERAL_CLARIFICATION',
                            'question_text': denial_message
                        }
                    }
                    
                    print(f"[HumanApprovalAgent] User denied confirmation, asking for clarification: {denial_message}")
                    
                return {
                    **state,
                        'human_approval_needed': True, # Re-trigger the pause
                        'approval_request': approval_request,
                        '__interrupt__': True
                }
            
            else:
                # Unknown response type, default to approval
                return {
                    **state,
                    'human_approval_needed': False,
                    'intent_approved': True,
                    'clarification_needed': False,
                    'human_response': human_response
                }
                
        except Exception as e:
            print(f"[HumanApprovalAgent] Error handling human response: {e}")
            return {
                **state,
                'human_approval_needed': False,
                'intent_approved': True,
                'clarification_needed': False,
                'human_response': human_response
            }