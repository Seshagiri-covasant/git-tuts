from flask import Flask
from flask_cors import CORS
from flask_executor import Executor
from config import config
from .repositories.chatbot_db_util import ChatbotDbUtil
from .utils.monitoring import setup_logging, db_monitor
from .utils.exceptions import (
    handle_validation_error,
    handle_service_exception,
    handle_general_exception,
    handle_not_found,
    ServiceException
)
from marshmallow import ValidationError

# Initialize extensions in the global scope of the factory module
executor = Executor()
cors = CORS()


def create_app(config_name):
    """
    Application Factory: Creates and configures the Flask app instance.
    """
    # This variable 'app' is the main Flask application instance.
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration
    app.config.from_object(config[config_name])

    # Configure executor for thread-based workers
    app.config['EXECUTOR_TYPE'] = 'thread'

    # Initialize extensions with the app instance
    executor.init_app(app)
    cors.init_app(app)

    # Setup application-wide logging
    setup_logging()

    # Initialize and store singleton objects in the app's config
    app.config['PROJECT_DB'] = ChatbotDbUtil()
    app.config['AGENTS_CACHE'] = {}
    app.config['BENCHMARK_STATUS'] = {}
    app.config['DB_MONITOR'] = db_monitor

    # Import and register the API blueprint
    from app.api.routes import app as api_blueprint
    from app.api import chatbot_routes, conversation_routes, template_routes, benchmark_routes, system_routes, validation_routes, settings_routes
    app.register_blueprint(api_blueprint, url_prefix='/api')

    # Register global error handlers
    app.register_error_handler(404, handle_not_found)
    app.register_error_handler(ValidationError, handle_validation_error)
    app.register_error_handler(ServiceException, handle_service_exception)
    app.register_error_handler(Exception, handle_general_exception)

    return app
