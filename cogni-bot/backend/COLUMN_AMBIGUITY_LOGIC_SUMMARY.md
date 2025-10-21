# 🎯 Column Ambiguity Detection Logic

## ✅ **Updated Logic**

### **When to Ask for Clarification:**
- **2+ similar columns** found that match the user's question
- Any ambiguity detected, not just 3+ columns

### **Improved Column Relevance Detection:**

#### **1. Business Terms Matching:**
```python
# Exact match required for business terms
for term in col_data.get('business_terms', []):
    if term.lower() in question_lower:
        return True
```

#### **2. Relevance Keywords Matching:**
```python
# Exact match required for relevance keywords
for keyword in col_data.get('relevance_keywords', []):
    if keyword.lower() in question_lower:
        return True
```

#### **3. Business Description Matching:**
```python
# Partial match for substantial descriptions
business_desc = col_data.get('business_description', '').lower()
if business_desc and len(business_desc) > 10:
    desc_words = set(word for word in business_desc.split() if len(word) > 3)
    if desc_words.intersection(question_terms):
        return True
```

#### **4. Column Name Matching:**
```python
# Exact match for column names
col_name = col_data.get('name', '').lower()
if col_name and col_name in question_lower:
    return True
```

#### **5. Common Pattern Matching:**
```python
# Pattern-based matching for common terms
common_patterns = ['risk', 'score', 'amount', 'date', 'time', 'value', 'total', 'count']
for pattern in common_patterns:
    if pattern in question_lower and pattern in col_name:
        return True
```

## 🎯 **Example Scenarios**

### **Scenario 1: Clear Question**
**User:** "Which payments have a risk score above 10?"
**Result:** Finds 1 relevant column → Proceeds with intelligent selection

### **Scenario 2: Ambiguous Question**
**User:** "Show me payments with risk scores"
**Result:** Finds 2+ relevant columns → Asks for clarification:

```
I found multiple columns that could be relevant to your question:

1. **Comprehensive risk assessment combining all risk factors** (Overall_Risk_Score) (Preferred) [HIGH] (Terms: overall risk, total risk, comprehensive risk)
2. **Machine learning predicted risk score** (ML_Risk_Score) (Terms: ML risk, predicted risk, AI risk)
3. **Transaction-specific risk score** (Overall_Tran_Risk_Score) (Terms: transaction risk, payment risk, tran risk)

Which column would you like me to use for your analysis?

You can respond with the number (1, 2, etc.) or describe which one you prefer.
```

### **Scenario 3: Very Similar Columns**
**User:** "Show me payment amounts"
**Result:** Finds multiple amount columns → Asks for clarification

## 🚀 **Benefits**

### **✅ Intelligent Detection:**
- Detects when multiple columns could match user intent
- Uses business metadata for accurate matching
- Considers user preferences and priority

### **✅ User-Friendly Questions:**
- Shows business descriptions, not technical names
- Indicates preferred and priority columns
- Shows business terms for context
- Allows multiple response formats (number or description)

### **✅ Flexible Responses:**
- User can respond with number: "1"
- User can respond with description: "the comprehensive one"
- User can respond with terms: "the ML one"

## 🎯 **Result**

The system now provides **intelligent column ambiguity detection** that asks for clarification when there are **2+ similar columns**, giving users clear choices with business context! 🎯✨
