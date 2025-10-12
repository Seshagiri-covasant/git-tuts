from app.repositories.chatbot_db_util import ChatbotDbUtil
import sys
import os
import logging

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def clear_stored_prompts():
    """Clear all stored chatbot prompts so they get regenerated with proper escaping"""
    try:
        # Connect to the chatbot database
        db = ChatbotDbUtil()

        # Clear all existing chatbot prompts
        with db.db_engine.begin() as connection:
            result = connection.execute(db.chatbot_prompt_table.delete())
            logging.info(
                f"Successfully cleared {result.rowcount} stored chatbot prompts and they will be regenerated correctly when you activate chatbots")

        return True
    except Exception as e:
        logging.info(f"Error clearing prompts: {e}")
        return False


if __name__ == "__main__":
    clear_stored_prompts()
