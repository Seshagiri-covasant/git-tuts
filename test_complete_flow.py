#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the complete clarification flow to ensure it works end-to-end
"""
import sys
sys.path.append('.')
from app.agents.query_clarification import QueryClarificationAgent
from app.repositories.chatbot_db_util import ChatbotDbUtil
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def test_complete_clarification_flow():
    print('🧪 Testing Complete Clarification Flow...')
    try:
        db = ChatbotDbUtil()
        agent = QueryClarificationAgent()
        
        # Simulate the conversation state with proper LangChain message objects
        conversation_history = [
            HumanMessage(content="Which payments have a risk score above 10?"),
            AIMessage(content="CLARIFICATION_NEEDED: I need a bit more information to help you better.\n\nI can see you're asking about risk scores in the Payments table. There are several risk score columns available: 'Overall_Tran_Risk_Score', 'ML_Risk_Score', and 'Overall_Risk_Score'. Which specific risk score column would you like me to use for your query?\n\nPlease provide your answer and I'll generate the most accurate query for you."),
            HumanMessage(content="Overall_Tran_Risk_Score")
        ]
        
        # Test the clarification logic with proper message format
        state = {
            'messages': conversation_history,
            'intent': {
                'tables': ['Payments'],
                'columns': [],
                'filters': ['Payments.Overall_Tran_Risk_Score > 10']
            }
        }
        
        print('📋 Testing clarification response detection...')
        result = agent.run(state, 'test', db)
        
        print(f'📊 Clarification needed: {result.get("clarification_needed", False)}')
        print(f'📊 Original question: {result.get("original_question", "None")}')
        
        if result.get("clarification_needed"):
            print('❌ Clarification is still being triggered - this means the response detection failed!')
        else:
            print('✅ Clarification response was detected and processed correctly!')
            
        # Check if the intent was updated with the selected column
        updated_intent = result.get('intent', {})
        columns = updated_intent.get('columns', [])
        print(f'📊 Updated columns: {columns}')
        
        if 'Overall_Tran_Risk_Score' in str(columns):
            print('✅ Column was correctly added to intent!')
        else:
            print('❌ Column was not added to intent!')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complete_clarification_flow()

