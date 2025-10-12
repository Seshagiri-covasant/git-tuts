import os
import atexit
from dotenv import load_dotenv
from app.factory import create_app
from app.repositories.app_db_util import cleanup_old_credential_files

# Load environment variables from .env file at the very beginning
load_dotenv()

# Clean up old credential files on startup
try:
    cleanup_old_credential_files(max_age_hours=24)
except Exception:
    pass # Non-critical, app should still start

# Get the environment config from an environment variable or use 'default'
config_name = os.getenv('FLASK_CONFIG') or 'default'

# Create the Flask app instance using our factory
app = create_app(config_name)

# Add shutdown handler for final cleanup
@atexit.register
def cleanup_on_shutdown():
    """Clean up resources when the application shuts down."""
    try:
        cleanup_old_credential_files(max_age_hours=0)  # Clean all files on shutdown
    except Exception:
        pass


if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    app.run(host=host, port=port)