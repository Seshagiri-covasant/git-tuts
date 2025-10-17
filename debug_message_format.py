#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug message format in conversation history
"""
import sys
sys.path.append('.')
from app.agents.agent_manager import AgentManager
from app.repositories.chatbot_db_util import ChatbotDbUtil

def debug_message_format():
    print('Testing message format...')
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
        
        print('Message format analysis:')
        for i, msg in enumerate(history):
            print(f'Message {i+1}:')
            print(f'  Type: {type(msg)}')
            if isinstance(msg, dict):
                print(f'  Keys: {list(msg.keys())}')
            else:
                print('  Not a dict')
            print(f'  Role: {msg.get("role", "unknown")}')
            print(f'  Content: {msg.get("content", "no content")[:100]}...')
            print()
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_message_format()

