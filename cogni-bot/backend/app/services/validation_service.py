from app.agents.llm_factory import get_llm
from .chatbot_service import get_chatbot_db
from app.benchmark_tools.testing_agents.validator_agent import ValidatorAgent
from flask import current_app
from .chatbot_service import get_chatbot_db
 
class ValidationService:
    """
    This service class encapsulates the business logic for validation tasks.
    It uses lazy initialization for the agent to work within Flask's app context.
    """
    def __init__(self):
        """
        Initializes the service. The agent is initialized as None and will be
        created on the first use.
        """
        self.query_comparison_agent = None
 
 
    def _get_agent(self):
        """
        A helper method to initialize the agent on its first use.
        This pattern is called "lazy initialization".
        """
        if self.query_comparison_agent is None:
            print("ValidationService: First use, initializing ValidatorAgent...")
            app_db_util = get_chatbot_db()
            self.query_comparison_agent = ValidatorAgent(llm=get_llm(), app_db_util=app_db_util)
        return self.query_comparison_agent
 
    def compare_sql_queries(
        self,
        natural_question: str,
        expected_sql: str,
        generated_sql: str
    ) -> dict:
        """
        Uses the ValidatorAgent to perform a semantic comparison of two SQL queries.
        """
        print(f"ValidationService: Comparing queries...")
        try:
            agent = self._get_agent()
           
            result = agent._llm_based_comparison(
                original_sql=expected_sql,
                generated_sql=generated_sql,
                nl_question=natural_question
               
            )
            return result
        except Exception as e:
            print(f"Error during query comparison in service: {e}")
            raise
 
validation_service = ValidationService()