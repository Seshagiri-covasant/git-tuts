#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REAL end-to-end test that simulates actual user interaction
"""
import sys
sys.path.append('.')
from app.agents.agent_manager import AgentManager
from app.repositories.chatbot_db_util import ChatbotDbUtil

def test_real_end_to_end():
    """Test the ACTUAL agent execution with real conversation history"""
    print('🧪 REAL End-to-End Test - Simulating Actual User Interaction')
    print('=' * 70)
    
    try:
        # Initialize components
        db = ChatbotDbUtil()
        agent = AgentManager(
            db_util=None,
            checkpoint=None,
            template='Test template',
            chatbot_db_util=db,
            chatbot_id='test'
        )
        
        test_conv_id = 'bd3d3270-5280-49ce-a749-5a80916e91d8'
        
        print('📊 Step 1: Check existing conversation history...')
        history = agent._get_conversation_history(test_conv_id)
        print(f'   Found {len(history)} messages in conversation history')
        
        if len(history) < 2:
            print('❌ Not enough conversation history for meaningful test')
            return
            
        print('📊 Step 2: Simulate a NEW query from user...')
        new_query = "Show me more details about these payments"
        print(f'   User sends: "{new_query}"')
        print('   This should be treated as a FOLLOW-UP query, not a new conversation')
        
        print('📊 Step 3: Execute agent with the new query...')
        print('   This will test if the agent uses conversation history properly')
        
        # This is the REAL test - does the agent use memory?
        try:
            result = agent.execute(
                conv_id=test_conv_id,
                request=new_query,
                llm_name=None,
                template=None,
                temperature=None
            )
            
            print('📊 Step 4: Analyze the result...')
            print(f'   Agent response type: {type(result)}')
            
            if isinstance(result, dict):
                final_result = result.get('final_result', 'No result')
                debug_info = result.get('debug', {})
                debug_steps = debug_info.get('steps', [])
                
                print(f'   Final result: {str(final_result)[:100]}...')
                print(f'   Debug steps: {len(debug_steps)}')
                
                # Check if the agent used conversation history
                print('📊 Step 5: Check if memory was used...')
                
                # Look for evidence that the agent used conversation history
                if 'risk score' in str(final_result).lower() or 'Overall_Tran_Risk_Score' in str(final_result):
                    print('✅ SUCCESS: Agent appears to have used conversation context!')
                    print('✅ The agent referenced risk score data from the previous conversation')
                else:
                    print('❌ CONCERN: Agent response does not show evidence of using conversation context')
                    print('❌ This might indicate the memory system is not working in practice')
                
                # Check debug information
                if debug_steps:
                    print('📊 Step 6: Analyzing debug information...')
                    for i, step in enumerate(debug_steps):
                        step_name = step.get('step', 'Unknown')
                        details = step.get('details', {})
                        print(f'   Step {i+1}: {step_name}')
                        
                        # Look for intent information
                        if 'intent' in details:
                            intent = details['intent']
                            print(f'      Intent tables: {intent.get("tables", [])}')
                            print(f'      Intent columns: {intent.get("columns", [])}')
                            
                            # Check if columns from previous conversation are used
                            if 'Overall_Tran_Risk_Score' in str(intent.get('columns', [])):
                                print('✅ SUCCESS: Agent used the column from previous conversation!')
                            else:
                                print('❌ CONCERN: Agent did not use columns from previous conversation')
                
            else:
                print(f'❌ Unexpected result type: {type(result)}')
                print(f'   Result: {result}')
                
        except Exception as e:
            print(f'❌ Error during agent execution: {e}')
            import traceback
            traceback.print_exc()
            
        print('=' * 70)
        print('🎯 REAL END-TO-END TEST COMPLETE')
        print()
        print('📋 HONEST ASSESSMENT:')
        print('This test shows whether the memory system actually works in practice.')
        print('If the agent uses conversation context, memory is working.')
        print('If the agent ignores conversation context, memory is NOT working.')
        
    except Exception as e:
        print(f'❌ Error during real end-to-end test: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_end_to_end()

