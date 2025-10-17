import sys
sys.path.append('.')
from app.agents.query_clarification import QueryClarificationAgent
from app.repositories.chatbot_db_util import ChatbotDbUtil
from langchain_core.messages import HumanMessage, AIMessage

print('Testing clarification response detection...')
try:
    db = ChatbotDbUtil()
    agent = QueryClarificationAgent()
    
    # Simulate conversation with proper LangChain messages
    conversation_history = [
        HumanMessage(content='Which payments have a risk score above 10?'),
        AIMessage(content='CLARIFICATION_NEEDED: I need a bit more information to help you better.'),
        HumanMessage(content='Overall_Tran_Risk_Score')
    ]
    
    state = {
        'messages': conversation_history,
        'intent': {
            'tables': ['Payments'],
            'columns': [],
            'filters': ['Payments.Overall_Tran_Risk_Score > 10']
        }
    }
    
    result = agent.run(state, 'test', db)
    
    print('Clarification needed:', result.get('clarification_needed', False))
    print('Original question:', result.get('original_question', 'None'))
    
    if not result.get('clarification_needed'):
        print('SUCCESS: Clarification response was detected!')
    else:
        print('FAILED: Still asking for clarification')
        
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()

