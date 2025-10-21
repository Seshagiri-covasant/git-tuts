# 🎯 Aggregation Patterns Flow - Complete System

## **🔄 Complete Flow: Frontend → Database → Agents**

### **1. Frontend Configuration (User Interface)**
```
User clicks "Aggregation Patterns" button
↓
AggregationPatternsDialog opens
↓
User creates/edits patterns:
- Pattern Name: "Percentage Analysis"
- Keywords: ["percentage", "breakdown", "vs", "versus"]
- SQL Template: "WITH threshold AS (SELECT AVG({score_column}) FROM {table})..."
- Example Question: "What percentage of high-risk payments are manual vs automated?"
↓
User clicks "Save Patterns"
↓
Patterns stored in component state: aggregationPatterns
```

### **2. Schema Storage (Database Persistence)**
```
User clicks "Save Changes" in schema editor
↓
handleSaveSchema() function called
↓
Patterns included in payloadSchema:
{
  "aggregation_patterns": [
    {
      "id": "percentage-analysis",
      "name": "Percentage Analysis",
      "keywords": ["percentage", "breakdown", "vs", "versus"],
      "sql_template": "WITH threshold AS (SELECT AVG({score_column}) FROM {table})...",
      "example_question": "What percentage of high-risk payments are manual vs automated?"
    }
  ]
}
↓
updateSemanticSchema() API call
↓
Patterns saved to database schema
```

### **3. Agent Usage (SQL Generation)**
```
User asks: "What percentage of high-risk payments are manual vs automated?"
↓
ConversationalIntentAnalyzer processes question
↓
Keywords "percentage" + "vs" match pattern
↓
QueryGenerator receives:
- User question
- Matched aggregation pattern
- Schema context
↓
QueryGenerator generates SQL:
WITH avg_risk AS (
    SELECT AVG(Overall_Tran_Risk_Score) AS avg_score
    FROM Payments
),
high_risk AS (
    SELECT IsManualPayment
    FROM Payments, avg_risk
    WHERE Overall_Tran_Risk_Score > avg_risk.avg_score
)
SELECT
    IsManualPayment,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS percentage,
    COUNT(*) AS count
FROM high_risk
GROUP BY IsManualPayment
```

## **📊 Data Flow Architecture:**

### **Frontend → Backend:**
1. **User Configuration:** Patterns created in UI
2. **State Management:** Patterns stored in React state
3. **Schema Integration:** Patterns included in schema payload
4. **API Call:** `updateSemanticSchema()` saves to database

### **Backend → Agents:**
1. **Schema Loading:** Agents load schema with patterns
2. **Pattern Matching:** Keywords matched to patterns
3. **SQL Generation:** Templates used to generate SQL
4. **Dynamic Substitution:** Placeholders replaced with actual values

## **🔧 Technical Implementation:**

### **Frontend (React):**
```typescript
// State management
const [aggregationPatterns, setAggregationPatterns] = useState<AggregationPattern[]>([]);

// Save to schema
const payloadSchema = {
  // ... other schema fields
  aggregation_patterns: aggregationPatterns,
  // ... rest of schema
};

// Load from schema
if (incoming.aggregation_patterns) {
  setAggregationPatterns(incoming.aggregation_patterns);
}
```

### **Backend (Database):**
```json
{
  "semantic_schema": {
    "tables": { ... },
    "metrics": [ ... ],
    "aggregation_patterns": [
      {
        "id": "percentage-analysis",
        "name": "Percentage Analysis",
        "keywords": ["percentage", "breakdown", "vs", "versus"],
        "sql_template": "WITH threshold AS (SELECT AVG({score_column}) FROM {table})...",
        "example_question": "What percentage of high-risk payments are manual vs automated?"
      }
    ]
  }
}
```

### **Agent Processing:**
```python
# Pattern matching
for pattern in schema.aggregation_patterns:
    if any(keyword in user_question.lower() for keyword in pattern.keywords):
        # Use pattern for SQL generation
        sql = pattern.sql_template.replace('{table}', 'Payments')
        sql = sql.replace('{score_column}', 'Overall_Tran_Risk_Score')
        sql = sql.replace('{group_column}', 'IsManualPayment')
        return sql
```

## **🎯 Key Benefits:**

### **✅ No Hardcoding:**
- Patterns stored in database, not code
- Users can modify patterns without code changes
- New patterns can be added through UI

### **✅ Dynamic SQL Generation:**
- Templates with placeholders for flexibility
- Automatic substitution based on schema
- Complex SQL generation without hardcoded logic

### **✅ User Configurable:**
- Visual interface for pattern management
- Clear examples and descriptions
- No technical knowledge required

## **🚀 Result:**

The system now has **complete end-to-end aggregation pattern support**:
- ✅ **Frontend Configuration:** User-friendly pattern creation
- ✅ **Database Storage:** Patterns persisted in schema
- ✅ **Agent Integration:** Patterns used for SQL generation
- ✅ **Dynamic Substitution:** Placeholders replaced with actual values

Users can now configure complex SQL generation patterns through the frontend, and the system will automatically use them to generate sophisticated SQL queries! 🎯✨
