#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify the memory fix works
"""
import sys
sys.path.append('.')
from app.agents.agent_manager import AgentManager
from app.repositories.chatbot_db_util import ChatbotDbUtil

def verify_fix():
    print('Testing the memory fix...')
    try:
        db = ChatbotDbUtil()
        agent = AgentManager(
            db_util=None,
            checkpoint=None,
            template='Test template',
            chatbot_db_util=db,
            chatbot_id='test'
        )
        
        test_conv_id = 'bd3d3270-5280-49ce-a749-5a80916e91d8'
        history = agent._get_conversation_history(test_conv_id)
        
        print(f'Retrieved {len(history)} messages')
        
        if history:
            first_msg = history[0]
            print(f'First message type: {type(first_msg)}')
            print(f'First message class: {first_msg.__class__.__name__}')
            
            is_human = first_msg.__class__.__name__ == 'HumanMessage'
            print(f'Is HumanMessage: {is_human}')
            
            if is_human:
                print('SUCCESS: Messages are now proper LangChain objects!')
                print('The memory system should now work correctly.')
            else:
                print('FAILED: Messages are still not proper LangChain objects.')
                
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_fix()

