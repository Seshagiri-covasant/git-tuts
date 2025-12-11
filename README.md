# SQL Agent Service

The **SQL Agent** is an intelligent orchestration engine designed to convert natural language user queries into executable T-SQL commands for Microsoft SQL Server. It utilizes Large Language Models (LLMs) combined with Retrieval-Augmented Generation (RAG) to ensure accurate, context-aware, and safe data retrieval.

---

## 🚀 Key Features

- **Natural Language to SQL:** Converts business questions (e.g., "who are top risky vendors") into optimized T-SQL.
- **Context Awareness:** Automatically detects the relevant Module (e.g., P2P) and Submodule (e.g., Invoices) using `ContextEvaluation` before querying.
- **Anti-Hallucination:** Validates generated SQL against the actual database schema to ensure only real tables and columns are used.
- **Safety & Optimization:**
  - Enforces a **1000-row limit** on open-ended queries to prevent large data.
  - Uses `sqlglot` to parse and sanitize queries (removing dangerous commands like DROP/DELETE).
- **RAG Implementation:** Uses FAISS-based semantic search to find relevant columns from the Data Dictionary, reducing token usage and improving accuracy.
- **Business Explanations:** Includes a secondary agent (`query_explainer.py`) that explains the generated SQL query in plain English to the user.
- **Interactive Filtering:** Capable of handling follow-up questions to refine `WHERE` clauses (e.g., "Filter by Country = US").
- **Intent Detection:** Distinguishes between "New Topic" queries and "Follow-up" refinements to maintain conversation context.

---

## 📂 Project Structure

The core logic resides in `code/src/sql_agent/`:

| File | Description |
|:-----|:------------|
| **`api.py`** | The FastAPI entry point (`/sqlagent`). Handles authentication and routes requests to the agent. |
| **`data_query.py`** | **The Core Orchestrator (`SQLQueryAgent`).** Manages the flow: Intent → SQL Generation → Validation → Execution → Formatting. |
| **`context_evaluation.py`** | Uses LLMs to determine the correct Module/Submodule based on user intent before SQL generation. Handles ambiguous queries by asking clarifying questions. |
| **`query_parser.py`** | A wrapper around `sqlglot`. Responsible for syntax validation, extracting table/column names, and safely injecting limits (`TOP 1000`). Handles CTEs, WITH TIES, and complex subqueries. |
| **`data_dictionary.py`** | Manages schema metadata. Syncs DB columns with descriptions to help the LLM understand the data. Validates that all columns have descriptions. |
| **`retriever.py`** | Performs **FAISS vector-based semantic search** to find the most relevant columns (top-k=20) for a specific user question. Uses text embeddings for RAG. |
| **`embedding.py`** | Text embedding utility for converting column descriptions into vectors for semantic search. |
| **`query_explainer.py`** | Generates business-friendly explanations for executed SQL queries using LLM. |
| **`filter_conditions.py`** | Manages interactive filter follow-up questions. Extracts WHERE clause conditions and presents them as user-selectable options. |
| **`prompt_catalogue.py`** | Custom prompt management system. Allows per-module/submodule customization of SQL generation rules and instructions. |
| **`errors.py`** | Custom exception classes: `HallucinationError`, `ConfigurationError`, `NotAllowedError` for better error handling and debugging. |
| **`UI/`** | Contains UI components for Data Dictionary management, Context Evaluation configuration, and Prompt Catalogue editor. |

---

## ⚙️ Logic Flow

```
1. [Request] User sends message via api.py
   ↓
2. [Context Check] context_evaluation.py determines Module/Submodule
   ↓ (If unclear, asks user for clarification)
3. [Pre-validation] Checks DB connection, table existence, data dictionary
   ↓
4. [Intent Detection] Determines "New Topic" vs "Follow-up" query
   ↓
5. [Schema Retrieval] retriever.py finds top 20 relevant columns via semantic search
   ↓
6. [Prompt Building] Constructs LLM prompt with schema + custom instructions
   ↓
7. [SQL Generation] LLM generates T-SQL based on retrieved schema
   ↓
8. [Text Cleaning] Removes LLM artifacts (explanations, alternatives)
   ↓
9. [Validation] query_parser.py checks:
   - Syntax validity (via sqlglot)
   - Table/column existence (anti-hallucination)
   - Only SELECT queries allowed
   ↓
10. [Limit Injection] Adds TOP 1000 if missing (handles CTEs, WITH TIES)
    ↓
11. [Filter Extraction] filter_conditions.py detects categorical filters
    ↓ (If found, presents follow-up questions)
12. [Execution] Runs query via database_config.py (Dask/Pandas)
    ↓
13. [Formatting] Converts results to JSON, formats datetime columns
    ↓
14. [Explanation] query_explainer.py generates plain English summary
    ↓
15. [Response] Returns data + explanation to user
```
---

## 🛠 Configuration & Setup

### Prerequisites

**Python 3.8+ with uv package manager**

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd KonaAI_ML

# Install dependencies using uv
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### Environment Variables

The project uses `INTELLIGENT_PATH` environment variable which points to the project data directory for storing:
- Database configurations
- Settings encryption keys
- Temporary files
- Log files

**Setup:**

```bash
# Set INTELLIGENT_PATH in your virtual environment
# This should point to your project_data directory
export INTELLIGENT_PATH=/path/to/KonaAI_ML/project_data  # Linux/Mac
set INTELLIGENT_PATH=C:\path\to\KonaAI_ML\project_data   # Windows CMD
$env:INTELLIGENT_PATH="C:\path\to\KonaAI_ML\project_data" # Windows PowerShell
```

### Data Dictionary Setup

To ensure accurate SQL generation, Data Dictionaries must be uploaded via the UI.

**Format:** Excel (`.xlsx`)

**Required Columns:**
- `COLUMN_NAME` - Database column name (VARCHAR)
- `DATA_TYPE` - SQL data type (VARCHAR, INTEGER, DECIMAL, etc.)
- `DESCRIPTION` - Business description (MUST NOT BE EMPTY)

**Example:**
| COLUMN_NAME | DATA_TYPE | DESCRIPTION |
|-------------|-----------|-------------|
| vendor_id | INTEGER | Unique vendor identifier |
| vendor_name | VARCHAR | Name of the vendor |
| risk_score | DECIMAL | Vendor risk score from 0-100 |

**Note:** Validation will fail if `DESCRIPTION` column is empty. Each column must have a meaningful business description to help the LLM generate accurate queries.

### LLM Configuration

**Recommended Model:** `gpt-4o-mini` (GPT-4.0-Mini)

**Why?**
- It has been observed that `gpt-4o-mini` provides better SQL generation results for this specific schema compared to `gpt-4.1-mini`.
- Faster response times (~2-3s average)
- Lower cost per query
- Better handling of complex T-SQL syntax

**Token Limits:**
- Query generation: 400 max tokens
- Explanations: 200 max tokens
- Context evaluation: 150 max tokens

---

## 🔗 API Endpoints

### POST `/sqlagent`

**Request:**
```json
{
  "thread_id": "uuid-string",
  "messages": [
    {
      "role": "user",
      "content": "who are top risky vendors",
      "content_type": "text"
    }
  ],
  "context": {
    "module": "P2P",
    "submodule": "Vendors",
    "instance_id": "client_instance_id"
  }
}
```

**Response:**
```json
{
  "thread_id": "uuid-string",
  "agent_id": "sql_query_agent",
  "messages": [
    {
      "role": "agent",
      "content": "[{\"vendor_name\": \"Vendor A\", \"risk_score\": 95.5}]",
      "content_type": "data_table"
    },
    {
      "role": "agent",
      "content": "This query retrieves the top 10 vendors sorted by risk score in descending order.",
      "content_type": "text"
    }
  ]
}
```

---

## 📊 Error Handling

The SQL Agent uses custom exceptions for better error tracking:

| Exception | When Raised | User Message |
|-----------|-------------|--------------|
| `HallucinationError` | LLM generates non-existent tables/columns | "Issue with SQL query generation due to LLM hallucination. Please rephrase your question." |
| `ConfigurationError` | DB connection issues or missing config | "Database configuration error. Please contact support." |
| `NotAllowedError` | Non-SELECT query attempted | "Only data retrieval operations are allowed." |
| `ValueError` | Empty query, missing context, etc. | "Couldn't generate a valid SQL query. Please try rephrasing." |

All errors are logged with full context for debugging while showing user-friendly messages to the end user.

---

## 📝 Known Behaviors

1. **Row Limit:** All queries are strictly limited to **1000 rows** for UI performance. This logic safely handles:
   - Simple SELECT queries
   - Complex CTEs (Common Table Expressions)
   - Queries with `WITH TIES` clause
   - Subqueries and window functions

2. **Schema Caching:** Column descriptions are cached in memory. If the database schema changes, the Data Dictionary must be re-uploaded/refreshed.

3. **Intent Context Window:** The agent remembers the last query context to distinguish follow-ups from new topics. Context is maintained per `thread_id`.

4. **Filter Follow-ups:** When a query contains categorical filters (e.g., `WHERE country = 'USA'`), the agent may ask follow-up questions to let users refine the filter interactively.

5. **Case Insensitivity:** SQL generation is case-insensitive for table/column names but preserves case in the final query for readability.

---

## 🐛 Troubleshooting

### Common Issues

**1. "No data dictionary found for table"**
- **Cause:** Data Dictionary not uploaded or uploaded for wrong table
- **Fix:** Upload Data Dictionary via UI for the correct `schema.table_name`

**2. "LLM did not return a response"**
- **Cause:** Azure OpenAI quota exhausted or network timeout
- **Fix:** Check API key, quota limits, and network connectivity

**3. "Hallucinated tables or columns found"**
- **Cause:** LLM invented non-existent schema elements
- **Fix:** Improve column descriptions in Data Dictionary. More detailed descriptions reduce hallucinations.

**4. "Only data retrieval operations are allowed"**
- **Cause:** User question resulted in DELETE/UPDATE/DROP query
- **Fix:** Rephrase question to be retrieval-focused (use words like "show", "list", "find")

**5. Empty results returned**
- **Cause:** Valid query but no matching data in DB
- **Fix:** Check if filters are too restrictive. Try broader query.

**6. "INTELLIGENT_PATH not set"**
- **Cause:** Environment variable not configured
- **Fix:** Set `INTELLIGENT_PATH` to point to `project_data/` directory before running the application

---

## 🚦 Performance Metrics

**Average Response Times:**
- Context evaluation: 800ms
- SQL generation: 2-3s
- Query execution: 500ms-2s (depends on data size)
- Explanation generation: 1-1.5s
- **Total end-to-end:** 4-7s








