# ✅ QueryGenerator Variables - Complete Definition Summary

## **🎯 Variables Defined in QueryGenerator**

### **1. ✅ `state` - Method Parameter**
```python
def run(self, state: dict, app_db_util=None, chatbot_db_util=None):
    """
    state: Dict containing all workflow state including:
    - user_question: User's original question
    - messages: Conversation history
    - knowledge_data: Schema data with patterns and preferences
    - intent: Parsed intent from previous agents
    - gathered_info: Information gathered by intent analyzer
    """
```

### **2. ✅ `aggregation_patterns` - Extracted from State**
```python
# Get aggregation patterns and AI preferences from knowledge data
aggregation_patterns = []
knowledge_data = state.get("knowledge_data", {})
if knowledge_data and isinstance(knowledge_data, dict):
    schema = knowledge_data.get("schema", {})
    if isinstance(schema, dict):
        aggregation_patterns = schema.get("aggregation_patterns", [])
        
        if aggregation_patterns:
            print(f"[QueryGenerator] Found {len(aggregation_patterns)} aggregation patterns")
            for pattern in aggregation_patterns:
                print(f"  - {pattern.get('name', 'Unknown')}: {pattern.get('keywords', [])}")
        else:
            print("[QueryGenerator] No aggregation patterns found in schema")
```

### **3. ✅ `ai_preferences` - Extracted from State**
```python
# Get aggregation patterns and AI preferences from knowledge data
ai_preferences = []
knowledge_data = state.get("knowledge_data", {})
if knowledge_data and isinstance(knowledge_data, dict):
    schema = knowledge_data.get("schema", {})
    if isinstance(schema, dict):
        ai_preferences = schema.get("ai_preferences", [])
        
        if ai_preferences:
            print(f"[QueryGenerator] Found {len(ai_preferences)} AI preferences")
            for preference in ai_preferences:
                print(f"  - {preference.get('name', 'Unknown')}: {preference.get('value', 'No value')}")
        else:
            print("[QueryGenerator] No AI preferences found in schema")
```

## **🔧 How Variables Are Used**

### **1. In LLM Prompt Generation**
```python
enhanced_prompt = f"""
You are a SQL query generator. Your task is to convert natural language questions into SQL queries.
{self.prompt_template}
DATABASE TYPE: {db_type.upper()}
{db_instructions}

DYNAMIC AGGREGATION PATTERNS:
{self._build_aggregation_patterns_section(aggregation_patterns, question)}

AI PREFERENCES:
{self._build_ai_preferences_section(ai_preferences)}

COMPLEX AGGREGATION PATTERNS:
- For percentage questions: Use COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () for percentages
- For "high" values: Use CTEs with AVG() to calculate thresholds, then filter WHERE column > threshold
- For comparisons (vs, versus): Use GROUP BY with the comparison column

Generate the SQL query:"""
```

### **2. In Helper Methods**
```python
def _build_aggregation_patterns_section(self, aggregation_patterns, question):
    """
    Build dynamic aggregation patterns section based on schema patterns and user question.
    """
    if not aggregation_patterns:
        return "No aggregation patterns configured in schema."
    
    # Find patterns that match the user question
    question_lower = question.lower() if question else ""
    matching_patterns = []
    
    for pattern in aggregation_patterns:
        keywords = pattern.get('keywords', [])
        if any(keyword.lower() in question_lower for keyword in keywords):
            matching_patterns.append(pattern)
    
    # Build the patterns section
    patterns_text = "MATCHING AGGREGATION PATTERNS:\n"
    for pattern in matching_patterns:
        patterns_text += f"\n- {pattern.get('name', 'Unknown Pattern')}:\n"
        patterns_text += f"  Keywords: {', '.join(pattern.get('keywords', []))}\n"
        patterns_text += f"  SQL Template: {pattern.get('sql_template', 'No template')}\n"
        patterns_text += f"  Example: {pattern.get('example_question', 'No example')}\n"
    
    patterns_text += "\nUse these patterns to generate appropriate SQL with proper placeholders replaced."
    return patterns_text

def _build_ai_preferences_section(self, ai_preferences):
    """
    Build AI preferences section for the LLM prompt.
    """
    if not ai_preferences:
        return "No AI preferences configured in schema."
    
    preferences_text = "CONFIGURED AI PREFERENCES:\n"
    for preference in ai_preferences:
        if isinstance(preference, dict):
            name = preference.get('name', 'Unknown Preference')
            value = preference.get('value', 'No value')
            description = preference.get('description', '')
            
            preferences_text += f"\n- {name}: {value}\n"
            if description:
                preferences_text += f"  Description: {description}\n"
    
    preferences_text += "\nUse these preferences to guide your SQL generation approach and style."
    return preferences_text
```

## **📊 Data Flow Summary**

### **1. State Flow**
```
AgentManager → state → QueryGenerator.run(state) → Extract patterns & preferences
```

### **2. Variable Extraction**
```
state.get("knowledge_data") → schema.get("aggregation_patterns") → aggregation_patterns
state.get("knowledge_data") → schema.get("ai_preferences") → ai_preferences
```

### **3. Usage in Prompt**
```
aggregation_patterns → _build_aggregation_patterns_section() → LLM Prompt
ai_preferences → _build_ai_preferences_section() → LLM Prompt
```

## **✅ Confirmation**

**All three variables are properly defined in QueryGenerator:**

1. **✅ `state`**: Method parameter passed from AgentManager
2. **✅ `aggregation_patterns`**: Extracted from `state["knowledge_data"]["schema"]["aggregation_patterns"]`
3. **✅ `ai_preferences`**: Extracted from `state["knowledge_data"]["schema"]["ai_preferences"]`

**All variables are:**
- ✅ **Properly defined** with correct data types
- ✅ **Extracted from state** with proper error handling
- ✅ **Used in LLM prompts** for intelligent SQL generation
- ✅ **Logged for debugging** to show what's being used
- ✅ **Passed to helper methods** for dynamic content generation

The QueryGenerator has complete access to all necessary data for sophisticated SQL generation! 🎯✨
