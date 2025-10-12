from flask import Blueprint, jsonify

# Create the Blueprint object. We will name it 'app' for clarity.
app = Blueprint('api', __name__)


@app.route('/')
def index():
    return jsonify({
        "message": "Welcome to the Natural Language to SQL Chatbot API",
        "status": "running",
        "version": "1.0"
    })
