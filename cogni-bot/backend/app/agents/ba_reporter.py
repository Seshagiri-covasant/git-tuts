"""
Business Analysis Reporter Agent

This agent generates business analysis summaries and reports based on query results.
"""

import json
from typing import Dict, List, Any, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage


class BAReporter:
    """
    Business Analysis Reporter for generating insights from query results.
    """
    
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
    
    def generate_summary(self, query_results: List[Dict], user_question: str, context: Dict[str, Any] = None) -> str:
        """
        Generate a business analysis summary from query results.
        
        Args:
            query_results: List of query result rows
            user_question: Original user question
            context: Additional context information
            
        Returns:
            Business analysis summary string
        """
        try:
            if not query_results:
                return "No data found matching your criteria."
            
            # Prepare data for analysis
            data_summary = self._prepare_data_summary(query_results)
            
            # Create analysis prompt
            analysis_prompt = self._create_analysis_prompt(user_question, data_summary, context)
            
            # Generate analysis using LLM
            response = self.llm.invoke([
                SystemMessage(content="You are a business analyst. Provide clear, actionable insights from the data."),
                HumanMessage(content=analysis_prompt)
            ])
            
            return response.content.strip()
            
        except Exception as e:
            return f"Error generating business analysis: {str(e)}"
    
    def _prepare_data_summary(self, query_results: List[Dict]) -> str:
        """Prepare a summary of the query results for analysis."""
        if not query_results:
            return "No data available"
        
        # Get column names
        columns = list(query_results[0].keys()) if query_results else []
        
        # Calculate basic statistics
        summary = {
            "total_records": len(query_results),
            "columns": columns,
            "sample_data": query_results[:5] if len(query_results) > 5 else query_results
        }
        
        return json.dumps(summary, indent=2)
    
    def _create_analysis_prompt(self, user_question: str, data_summary: str, context: Dict[str, Any] = None) -> str:
        """Create a prompt for business analysis."""
        context_info = ""
        if context:
            context_info = f"\nAdditional Context: {json.dumps(context, indent=2)}"
        
        prompt = f"""
Please analyze the following data and provide business insights:

User Question: {user_question}

Data Summary:
{data_summary}
{context_info}

Please provide:
1. Key findings from the data
2. Business implications
3. Recommendations or next steps
4. Any patterns or trends observed

Keep the analysis concise but informative, focusing on actionable business insights.
"""
        return prompt


def generate_llm_ba_summary(query_results: List[Dict], user_question: str, llm: BaseLanguageModel, context: Dict[str, Any] = None) -> str:
    """
    Generate a business analysis summary using LLM.
    
    Args:
        query_results: List of query result rows
        user_question: Original user question
        llm: Language model instance
        context: Additional context information
        
    Returns:
        Business analysis summary string
    """
    reporter = BAReporter(llm)
    return reporter.generate_summary(query_results, user_question, context)


def generate_basic_summary(query_results: List[Dict], user_question: str) -> str:
    """
    Generate a basic summary without LLM.
    
    Args:
        query_results: List of query result rows
        user_question: Original user question
        
    Returns:
        Basic summary string
    """
    if not query_results:
        return "No data found matching your criteria."
    
    total_records = len(query_results)
    columns = list(query_results[0].keys()) if query_results else []
    
    summary = f"Found {total_records} records matching your query."
    if columns:
        summary += f" The data includes columns: {', '.join(columns)}."
    
    return summary
