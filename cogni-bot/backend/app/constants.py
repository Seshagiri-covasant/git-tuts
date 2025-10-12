# --- Supported LLM and Database Types ---
LLM_NAMES = ["COHERE", "CLAUDE", "GEMINI", "OPENAI", "AZURE"]
DB_TYPES = ["sqlite", "postgresql", "bigquery", "mysql", "mssql"]

# --- LLM Model Name Constants ---
LLM_MODELS = {
    "AZURE": "gpt-4o-mini",
    "OPENAI": "gpt-4o-mini",
    "COHERE": "command-a-03-2025",
    "GEMINI": "gemini-1.5-pro-latest",
    "CLAUDE": "claude-sonnet-4-20250514",
}

# --- Default Values ---
DEFAULT_LLM_NAME = "COHERE"
DEFAULT_TEMPERATURE = 0.7

# --- Benchmark and Testing Constants ---
BENCHMARK_CONVERSATION_NAME = "Test Suite"
BENCHMARK_CONVERSATION_OWNER = "TestAdmin"


SCHEMA_CACHE_EXPIRATION_HOURS = 24

MAX_INTERACTIONS_PER_CONVERSATION = 10
