# Agent Thoughts Guide - How to See Agent Intent Picking

## 🎯 Overview

The enhanced conversational intent analyzer system provides comprehensive logging of agent thoughts and reasoning. This guide shows you exactly how to see what agents are thinking and why they make their decisions.

## 🔍 Agent Thoughts in Action

### 1. **Intent Analysis Thoughts**

When an agent analyzes user intent, you'll see thoughts like:

```
[AGENT THOUGHT] Starting intent analysis for: 'Which payments have a risk score above 10?'
[AGENT THOUGHT] Analyzing question structure and keywords
[AGENT THOUGHT] Mapping question to available database schema
[AGENT THOUGHT] Detected risk-related query - mapping to risk_score column
[AGENT THOUGHT] Found filter condition: 'above 10' - creating WHERE clause
[AGENT THOUGHT] Intent analysis complete: SELECT
[AGENT THOUGHT] Proceeding with SELECT query generation
```

### 2. **SQL Generation Thoughts**

When generating SQL, you'll see:

```
[AGENT THOUGHT] Starting SQL generation based on intent: SELECT
[AGENT THOUGHT] Selected tables: ['payments']
[AGENT THOUGHT] Selected columns: ['*']
[AGENT THOUGHT] Applying filters: ['risk_score > 10']
[AGENT THOUGHT] Generated SQL: SELECT * FROM payments WHERE risk_score > 10;
```

### 3. **Query Validation Thoughts**

When validating queries, you'll see:

```
[AGENT THOUGHT] Starting query validation for: SELECT * FROM payments WHERE risk_score > 10
[AGENT THOUGHT] Checking SQL syntax - appears valid
[AGENT THOUGHT] Checking schema compliance - tables and columns exist
[AGENT THOUGHT] Security analysis - no injection vulnerabilities detected
[AGENT THOUGHT] Performance analysis - query should execute efficiently
[AGENT THOUGHT] Query validation complete - VALID
```

## 🚀 How to See Agent Thoughts in Your System

### Method 1: Backend Terminal Logs

When you run your backend server, you'll see agent thoughts in the terminal output:

```bash
cd cogni-bot/backend
python main.py
```

Then when you ask a question in the frontend, you'll see logs like:

```
================================================================================
🤖 AGENT THOUGHTS: AdvancedConversationalIntentAnalyzer
================================================================================
💭 [AGENT THOUGHT] Starting intent analysis for: 'Which payments have a risk score above 10?'
💭 [AGENT THOUGHT] Analyzing question structure and keywords
💭 [AGENT THOUGHT] Mapping question to available database schema
💭 [AGENT THOUGHT] Detected risk-related query - mapping to risk_score column
💭 [AGENT THOUGHT] Found filter condition: 'above 10' - creating WHERE clause
💭 [AGENT THOUGHT] Intent analysis complete: SELECT
💭 [AGENT THOUGHT] Proceeding with SELECT query generation
```

### Method 2: Enhanced Agent Manager

The `EnhancedAgentManager` provides comprehensive thought tracking:

```python
from app.agents.enhanced_agent_manager import EnhancedAgentManager
from app.agents.llm_factory import get_llm

# Initialize
llm = get_llm()
agent_manager = EnhancedAgentManager(llm, chatbot_db_util, chatbot_id, app_db_util)

# Execute workflow
state = {
    'user_question': 'Which payments have a risk score above 10?',
    'conversation_history': [],
    'agent_thoughts': []
}

result = agent_manager.execute(state)

# Get all agent thoughts
agent_thoughts = result.get('agent_thoughts', [])
for thought in agent_thoughts:
    print(f"💭 {thought}")
```

### Method 3: Individual Agent Thoughts

Each enhanced agent tracks its own thoughts:

```python
from app.agents.enhanced_intent_picker import EnhancedIntentPicker
from app.agents.enhanced_query_generator import EnhancedQueryGenerator
from app.agents.enhanced_query_validator import EnhancedQueryValidator

# Intent Picker Thoughts
intent_picker = EnhancedIntentPicker(llm)
result = intent_picker.pick_intent(state)
intent_thoughts = result.get('agent_thoughts', [])

# Query Generator Thoughts
query_generator = EnhancedQueryGenerator(llm, app_db_util, chatbot_db_util, chatbot_id)
result = query_generator.generate_query(state)
generation_thoughts = result.get('agent_thoughts', [])

# Query Validator Thoughts
query_validator = EnhancedQueryValidator(llm)
result = query_validator.validate_query(state)
validation_thoughts = result.get('agent_thoughts', [])
```

## 📊 Understanding Agent Decision Making

### Intent Picking Process

1. **Question Analysis**: Agent analyzes the user's question structure
2. **Keyword Detection**: Identifies key terms like "risk score", "above", "payments"
3. **Schema Mapping**: Maps question to available database schema
4. **Intent Determination**: Decides what type of query is needed
5. **Confidence Assessment**: Evaluates confidence in the analysis

### SQL Generation Process

1. **Intent Analysis**: Understands what data to retrieve
2. **Table Selection**: Chooses relevant tables
3. **Column Selection**: Determines which columns to include
4. **Filter Application**: Applies WHERE conditions
5. **Query Construction**: Builds the final SQL query

### Validation Process

1. **Syntax Check**: Validates SQL syntax
2. **Schema Compliance**: Ensures tables/columns exist
3. **Security Analysis**: Checks for injection vulnerabilities
4. **Performance Analysis**: Evaluates query efficiency
5. **Final Validation**: Confirms query is ready for execution

## 🔧 Configuration for Agent Thoughts

### Enable Detailed Logging

In your backend configuration, ensure logging is set to INFO level:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Custom Thought Formatting

You can customize how thoughts are displayed:

```python
# In each agent, thoughts are formatted as:
thought = f"[AGENT THOUGHT] {description}"
self.agent_thoughts.append(thought)
print(f"💭 {thought}")
```

### Thought Categories

Agent thoughts are categorized by type:

- **`[AGENT THOUGHT]`**: General reasoning and decision-making
- **`[AGENT ERROR]`**: Error conditions and fallbacks
- **`[MANAGER THOUGHT]`**: Workflow orchestration decisions
- **`[LLM RESPONSE]`**: Raw LLM responses and analysis

## 🎯 Example: Complete Agent Thought Flow

Here's what you'll see for the question "Which payments have a risk score above 10?":

```
================================================================================
🎯 ENHANCED AGENT MANAGER: Starting Workflow
================================================================================
💭 [MANAGER THOUGHT] Starting enhanced workflow for: 'Which payments have a risk score above 10?'
💭 [MANAGER THOUGHT] Schema loaded: 3 tables, 2 metrics

================================================================================
🔍 STEP 1: Intent Analysis
================================================================================
💭 [AGENT THOUGHT] Starting intent analysis for: 'Which payments have a risk score above 10?'
💭 [AGENT THOUGHT] Analyzing question structure and keywords
💭 [AGENT THOUGHT] Mapping question to available database schema
💭 [AGENT THOUGHT] Detected risk-related query - mapping to risk_score column
💭 [AGENT THOUGHT] Found filter condition: 'above 10' - creating WHERE clause
💭 [AGENT THOUGHT] Intent analysis complete: SELECT

================================================================================
🔧 STEP 2: Query Generation
================================================================================
💭 [AGENT THOUGHT] Starting SQL generation based on intent: SELECT
💭 [AGENT THOUGHT] Selected tables: ['payments']
💭 [AGENT THOUGHT] Selected columns: ['*']
💭 [AGENT THOUGHT] Applying filters: ['risk_score > 10']
💭 [AGENT THOUGHT] Generated SQL: SELECT * FROM payments WHERE risk_score > 10;

================================================================================
✅ STEP 3: Query Validation
================================================================================
💭 [AGENT THOUGHT] Starting query validation for: SELECT * FROM payments WHERE risk_score > 10
💭 [AGENT THOUGHT] Checking SQL syntax - appears valid
💭 [AGENT THOUGHT] Checking schema compliance - tables and columns exist
💭 [AGENT THOUGHT] Security analysis - no injection vulnerabilities detected
💭 [AGENT THOUGHT] Performance analysis - query should execute efficiently
💭 [AGENT THOUGHT] Query validation complete - VALID

================================================================================
🚀 STEP 4: Query Execution
================================================================================
💭 [AGENT THOUGHT] Starting query execution for: SELECT * FROM payments WHERE risk_score > 10
💭 [AGENT THOUGHT] Query execution complete: Success
💭 [MANAGER THOUGHT] Workflow completed with status: completed
```

## 🛠️ Troubleshooting Agent Thoughts

### If You Don't See Thoughts

1. **Check Logging Level**: Ensure logging is set to INFO or DEBUG
2. **Verify Agent Type**: Make sure you're using the enhanced agents
3. **Check Console Output**: Thoughts are printed to console, not just logged
4. **Verify Import**: Ensure you're importing the enhanced agent classes

### Common Issues

1. **Unicode Errors**: Remove emoji characters if running on Windows
2. **Missing LLM**: Ensure LLM is properly configured
3. **Import Errors**: Check that all enhanced agents are properly imported
4. **State Issues**: Ensure state is properly passed between agents

## 📈 Benefits of Agent Thoughts

1. **Complete Visibility**: See exactly how agents make decisions
2. **Debugging**: Easily identify where issues occur in the workflow
3. **Optimization**: Understand which parts of the process need improvement
4. **User Experience**: Provide transparency into the AI's reasoning
5. **Development**: Help developers understand and improve the system

## 🎯 Next Steps

1. **Run the Backend**: Start your backend server to see thoughts in action
2. **Ask Questions**: Use the frontend to ask questions and watch the terminal
3. **Analyze Thoughts**: Review the agent thoughts to understand decision-making
4. **Customize**: Modify thought formatting or add additional logging as needed
5. **Optimize**: Use insights from thoughts to improve agent performance

---

**Agent Thoughts** provide complete transparency into how the conversational intent analyzer makes decisions, helping you understand and optimize the AI's reasoning process! 🚀
