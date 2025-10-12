from flask import Blueprint, request, jsonify
 
from app.api.routes import app
from app.services.validation_service import validation_service
 
@app.route('/compare-queries', methods=['POST'])
def compare_queries_endpoint():
    data = request.get_json()
   
    required_keys = ['natural_question', 'query1', 'query2']
    if not all(key in data for key in required_keys):
        return jsonify({"error": f"Request body must include {required_keys}"}), 400
    try:
        result = validation_service.compare_sql_queries(
            natural_question=data['natural_question'],
            expected_sql=data['query1'],
            generated_sql=data['query2']
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500