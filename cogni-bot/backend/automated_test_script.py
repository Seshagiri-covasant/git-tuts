import os
import json
import yaml
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from typing import Dict, Any
 
load_dotenv()
 
# --- Configuration & Setup ---
COGNIBOT_API_URL = "http://127.0.0.1:5000"
YAML_FILE_PATH = "test_suite.yaml"
CONVERSATION_OWNER = "TestSuiteRunner"
CONVERSATION_INTERACTION_LIMIT = 10
 
# --- Helper Functions ---
def load_tests_from_yaml(file_path: str) -> Dict[str, Any]:
    """Loads and validates the test suite from a YAML file."""
    try:
        with open(file_path, 'r') as f: return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading or parsing YAML file: {e}")
        return {}
 
def create_new_conversation(chatbot_id: str, conversation_name: str) -> str:
    """Creates a new conversation for a given chatbot and returns the conversation ID."""
    url = f"{COGNIBOT_API_URL}/api/chatbots/{chatbot_id}/conversations"
    payload = {"conversation_name": conversation_name, "owner": CONVERSATION_OWNER}
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()["conversation"]["conversationId"]
    except requests.exceptions.RequestException as e:
        print(f"    ERROR: Could not create conversation. API responded with: {e.response.text if e.response else e}")
        return ""
 
def get_generated_sql_from_cognibot(conversation_id: str, natural_question: str) -> str:
    """Sends a question to the Cognibot API and returns the generated SQL."""
    url = f"{COGNIBOT_API_URL}/api/conversations/{conversation_id}/interactions"
    payload = {"request": natural_question}
    try:
        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()
        response_data = response.json()
        return response_data.get("cleaned_query", "NO_SQL_RETURNED")
    except requests.exceptions.RequestException as e:
        return f"API_ERROR: {e.response.text if e.response else e}"
 
def validate_queries(natural_question: str, generated_sql: str, expected_sql: str) -> (str, str):
    """
    Validates queries by calling the backend's ValidatorAgent.
    Returns (status, reason) where status is 'PASS' or 'FAIL'.
    """
    if not generated_sql or "API_ERROR" in generated_sql or "NO_SQL_RETURNED" in generated_sql:
        return "FAIL", f"Failed to generate SQL from API: {generated_sql}"
 
    url = f"{COGNIBOT_API_URL}/api/compare-queries"
    payload = {
        "natural_question": natural_question,
        "query1": expected_sql,
        "query2": generated_sql
    }
    try:
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
       
        # Your new agent returns a simple string response
        agent_verdict = response.text.strip().lower().replace('"', '')
 
        if agent_verdict == "yes":
            return "PASS", "Agent confirmed semantic match."
        elif agent_verdict == "no":
            return "FAIL", "Agent determined queries are not equivalent."
        else: # Handles "ambiguous" or any other response
            return "FAIL", f"Agent gave an ambiguous response: '{agent_verdict}'"
 
    except requests.exceptions.RequestException as e:
        return "FAIL", f"API call to comparison agent failed: {e.response.text if e.response else e}"
 
# --- Main Test Runner  ---
def run_test_suite():
    test_suite_data = load_tests_from_yaml(YAML_FILE_PATH)
    if not test_suite_data: return
   
    chatbot_id = test_suite_data.get("chatbot_id")
    test_sets = test_suite_data.get("test_sets", [])
    if not chatbot_id:
        print("Error: 'chatbot_id' not found in YAML. Aborting.")
        return
 
    all_results = []
    print(f"\nStarting Automated Test Suite for Cognibot (ID: {chatbot_id})...\n")
   
    total_tests = sum(len(ts.get("questions", [])) for ts in test_sets)
    current_test_num = 0
 
    for test_set in test_sets:
        set_name = test_set.get("test_set", "Unnamed Set")
        questions = test_set.get("questions", [])
        if not questions: continue
       
        print(f"--- Running Test Set: {set_name} ---")
 
        conversation_id = None
        interaction_counter = CONVERSATION_INTERACTION_LIMIT
        conversation_part = 1
 
        for qa_pair in questions:
            current_test_num += 1
           
            if interaction_counter >= CONVERSATION_INTERACTION_LIMIT:
                print(f"\n  ... Creating new conversation for '{set_name}' (Part {conversation_part})...")
                conversation_id = create_new_conversation(chatbot_id, f"Test Suite - {set_name} Part {conversation_part}")
                if not conversation_id:
                    print(f"    FAIL: Could not create new conversation. Skipping remaining tests in this set.")
                    break
                interaction_counter = 0
                conversation_part += 1
 
            natural_question = qa_pair.get("natural_question")
            expected_sql = qa_pair.get("expected_sql").strip()
           
            print(f"\n({current_test_num}/{total_tests}) Question: {natural_question}")
           
            generated_sql = get_generated_sql_from_cognibot(conversation_id, natural_question)
            if isinstance(generated_sql, str): generated_sql = generated_sql.strip()
 
            print(f"  - Expected SQL:\n      {expected_sql.replace('\n', '\n      ')}")
            print(f"  - Generated SQL:\n      {generated_sql.replace('\n', '\n      ') if generated_sql else 'None'}")
 
            status, reason = validate_queries(natural_question, generated_sql, expected_sql)
           
            status_text = "***PASS***" if status == "PASS" else "***FAIL***"
            print(f"  - Status: {status_text} ({reason})")
           
            all_results.append({
                "Test Set": set_name, "Chatbot ID": chatbot_id,
                "Natural Question": natural_question, "Expected SQL": expected_sql,
                "Generated SQL": generated_sql, "Status": status, "Reason": reason
            })
 
            interaction_counter += 1
 
    # --- Generate and Print Summary Report ---
    print("\n\n---Test Suite Summary ---")
    if not all_results:
        print("No tests were run.")
        return
    df = pd.DataFrame(all_results)
    summary = df.groupby("Test Set")["Status"].value_counts().unstack(fill_value=0)
    for col in ['PASS', 'FAIL']:
        if col not in summary.columns: summary[col] = 0
    summary["Total"] = summary["PASS"] + summary["FAIL"]
    summary["Pass Rate"] = (summary["PASS"] / summary["Total"] * 100).map('{:.2f}%'.format)
    print(summary.to_string())
    report_filename = "test_suite_report.csv"
    df.to_csv(report_filename, index=False)
    print(f"\nDetailed report saved to '{report_filename}'")
 
if __name__ == "__main__":
    run_test_suite()