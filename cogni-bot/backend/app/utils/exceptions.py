import logging
import traceback
from flask import jsonify

# --- Agent-Specific Exceptions ---


class QueryGenerationException(Exception):
    pass


class QueryExecutionException(Exception):
    pass


class QueryCleanupException(Exception):
    pass


class WorkflowExecutionException(Exception):
    pass

# --- Service Layer Exception ---


class ServiceException(Exception):
    """Custom exception for service layer errors to ensure consistent API responses."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code

# --- Global Error Handlers ---


def handle_validation_error(e):
    """Handles Marshmallow validation errors."""
    return jsonify({"error": "Validation failed", "messages": e.messages}), 400


def handle_service_exception(e):
    """Handles custom service layer exceptions."""
    return jsonify({"error": str(e)}), e.status_code


def handle_not_found(e):
    return jsonify({"error": "The requested resource was not found"}), 404


def handle_general_exception(e):
    """Handles all other unexpected exceptions."""
    # Log the full traceback for debugging
    logging.error(traceback.format_exc())

    # Handle known agent exceptions with specific messages
    if isinstance(e, (QueryGenerationException, QueryExecutionException, QueryCleanupException, WorkflowExecutionException)):
        return jsonify({"error": f"Agent workflow error: {str(e)}"}), 500

    return jsonify({"error": "An internal server error occurred."}), 500
