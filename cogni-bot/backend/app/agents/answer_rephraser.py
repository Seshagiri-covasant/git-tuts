import json
from ..utils.exceptions import WorkflowExecutionException


class AnswerRephraser:
    def __init__(self, query_generator=None, chatbot_db_util=None):
        self.query_generator = query_generator
        self.chatbot_db_util = chatbot_db_util  # For chatbot-related data if needed

    def run(self, state: dict, app_db_util=None, chatbot_db_util=None, **kwargs):
        try:
            # Use app_db_util for any application-specific query execution if needed
            result_str = state["messages"][-1]

            if hasattr(result_str, "content"):
                result_str = result_str.content

            # First try to parse as JSON
            try:
                data = json.loads(result_str) if isinstance(
                    result_str, str) else result_str

                # Check if this is an error message
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    if "error" in data[0]:
                        return {"messages": [json.dumps(data)]}

                # If it's not an error, just return the data
                try:
                    print(f"[Answer_Rephraser] Final payload preview: {json.dumps(data)[:1000]}")
                except Exception:
                    pass
                return {"messages": [json.dumps(data)]}

            except Exception:
                # If JSON parsing fails, handle as regular message
                pass

            # Handle non-JSON messages
            if isinstance(result_str, str):
                if state.get("forbidden_sql", False) or "not allowed to run data-modification" in result_str:
                    return {"messages": [result_str]}
                else:
                    try:
                        print(f"[Answer_Rephraser] Final message: {result_str[:1000]}")
                    except Exception:
                        pass
                    return {"messages": [result_str]}

            # If we get here and have no data, return empty message
            return {"messages": ["No data found."]}

        except Exception as e:
            raise WorkflowExecutionException(e)
