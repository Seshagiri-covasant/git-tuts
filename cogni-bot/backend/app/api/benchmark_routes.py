
from flask import jsonify
from app.api.routes import app
from ..services import benchmark_service

# --- Standard Benchmark Routes ---


@app.route("/chatbots/<chatbot_id>/benchmark", methods=["POST"])
def start_benchmark_route(chatbot_id):
    result = benchmark_service.start_benchmark_service(chatbot_id)
    return jsonify(result), 202


@app.route("/chatbots/<chatbot_id>/benchmark", methods=["GET"])
def get_benchmark_status_route(chatbot_id):
    return jsonify(benchmark_service.get_benchmark_status_service(chatbot_id))


@app.route('/chatbots/<chatbot_id>/benchmark/details', methods=['GET'])
def get_benchmark_details_route(chatbot_id):
    return jsonify(benchmark_service.get_benchmark_details_service(chatbot_id))


@app.route('/chatbots/<chatbot_id>/performance', methods=['GET'])
def get_performance_metrics_route(chatbot_id):
    return jsonify(benchmark_service.get_performance_metrics_service(chatbot_id))


@app.route('/chatbots/<chatbot_id>/benchmark/cleanup', methods=['POST'])
def cleanup_benchmark_data_route(chatbot_id):
    return jsonify(benchmark_service.cleanup_benchmark_data_service(chatbot_id))

# --- Custom Test Suite Routes ---


@app.route('/chatbots/<chatbot_id>/custom-tests', methods=['POST'])
def create_custom_test_route(chatbot_id):
    test = benchmark_service.create_custom_test_service(chatbot_id)
    return jsonify({"message": "Custom test created successfully", "test": test}), 201


@app.route('/chatbots/<chatbot_id>/custom-tests', methods=['GET'])
def get_custom_tests_route(chatbot_id):
    return jsonify(benchmark_service.get_custom_tests_service(chatbot_id))


@app.route('/chatbots/<chatbot_id>/custom-tests/suites', methods=['GET'])
def get_custom_test_suites_route(chatbot_id):
    return jsonify(benchmark_service.get_custom_test_suites_service(chatbot_id))


@app.route('/chatbots/<chatbot_id>/custom-tests/run', methods=['POST'])
def run_custom_tests_route(chatbot_id):
    result = benchmark_service.run_custom_tests_service(chatbot_id)
    return jsonify(result), 202


@app.route('/chatbots/<chatbot_id>/custom-tests/metrics', methods=['GET'])
def get_custom_test_metrics_route(chatbot_id):
    return jsonify(benchmark_service.get_custom_test_metrics_service(chatbot_id))


@app.route('/custom-tests/<test_id>', methods=['DELETE'])
def delete_custom_test_route(test_id):
    return jsonify(benchmark_service.delete_custom_test_service(test_id))
