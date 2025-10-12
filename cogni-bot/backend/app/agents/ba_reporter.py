import json
import logging
from .llm_factory import get_llm
from ..utils.prompt_loader import get_prompt


def generate_llm_ba_summary(table, user_query, chatbot_id= None, llm_name=None, temperature=None):
    """
    Generates a business analysis summary of table data based on a user query,
    using the currently configured LLM for the chatbot.
    """
    try:
        llm = get_llm(llm_name=llm_name, temperature=temperature)

        prompt = get_prompt(
            "data_analysis/ba_summary.txt",
            user_query=user_query,
            table_data=json.dumps(table, indent=2)
        )

        response = llm.invoke(prompt)

        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    except Exception as e:
        logging.error(f"Error generating BA summary: {e}", exc_info=True)
        return "An error occurred while generating the business analysis summary."
