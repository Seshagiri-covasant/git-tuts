import logging
import os
import time
import psutil
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from flask import current_app

# --- Logging Setup ---


def setup_logging():
    """Initializes and configures the application's logging system."""

    # 1. Define the path for the logs directory.
    log_dir = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), '..', '..', 'logs')

    # 2. Ensure the logs directory exists.
    os.makedirs(log_dir, exist_ok=True)

    # 3. Define the full path for the log file.
    log_file_path = os.path.join(log_dir, 'app.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ]
    )
    # Create specific loggers to allow for more granular control if needed later
    logging.getLogger('database')
    logging.getLogger('memory')
    logging.getLogger('performance')


# --- Database and System Monitoring Class ---
class DatabaseMonitor:
    """A class to handle monitoring of database connections and system resources."""

    def __init__(self):
        self.connection_stats = {}
        self.last_cleanup = time.time()

    def log_connection_pool_status(self, engine, db_name="unknown"):
        """Log current connection pool status for a given SQLAlchemy engine."""
        try:
            if hasattr(engine, 'pool') and isinstance(engine.pool, QueuePool):
                pool = engine.pool
                stats = {
                    'db_name': db_name,
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'timestamp': time.time()
                }

                try:
                    stats['invalid'] = pool.invalid()
                except AttributeError:
                    # Not all pool types support invalid()
                    stats['invalid'] = 0

                self.connection_stats[db_name] = stats

                db_logger = logging.getLogger('database')
                db_logger.info(f"DB Pool Status - {db_name}: "
                               f"Size={stats['pool_size']}, CheckedIn={stats['checked_in']}, "
                               f"CheckedOut={stats['checked_out']}, Overflow={stats['overflow']}, "
                               f"Invalid={stats['invalid']}")

                # Log warnings for potential issues
                if stats['checked_out'] > stats['pool_size'] * 0.8:
                    db_logger.warning(f"High connection usage for {db_name}: "
                                      f"{stats['checked_out']}/{stats['pool_size']} connections in use.")
                if stats['overflow'] > 0:
                    db_logger.warning(
                        f"Connection overflow for {db_name}: {stats['overflow']} overflow connections.")
                if stats['invalid'] > 0:
                    db_logger.error(
                        f"Invalid connections detected for {db_name}: {stats['invalid']}.")
            else:
                logging.getLogger('database').info(
                    f"No QueuePool found for {db_name}, cannot report status.")

        except Exception as e:
            logging.getLogger('database').error(
                f"Error logging connection pool status for {db_name}: {e}")

    def log_memory_usage(self):
        """Log current memory usage of the application process and system."""
        try:
            memory_logger = logging.getLogger('memory')
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            system_memory = psutil.virtual_memory()

            memory_logger.info(f"Memory Usage - "
                               f"Process RSS: {memory_info.rss / 1024 / 1024:.1f}MB, "
                               f"Process VMS: {memory_info.vms / 1024 / 1024:.1f}MB, "
                               f"Process Percent: {memory_percent:.1f}%, "
                               f"System Percent: {system_memory.percent:.1f}% "
                               f"(Available: {system_memory.available / 1024 / 1024 / 1024:.1f}GB)")

            # Log warnings for high memory usage
            if memory_percent > 80:
                memory_logger.warning(
                    f"High process memory usage detected: {memory_percent:.1f}%")
            if system_memory.percent > 90:
                memory_logger.warning(
                    f"High system memory usage detected: {system_memory.percent:.1f}%")

        except Exception as e:
            logging.getLogger('memory').error(
                f"Error logging memory usage: {e}")

    def log_performance_metrics(self, operation, duration, db_name="unknown"):
        """Log performance metrics for database operations."""
        try:
            performance_logger = logging.getLogger('performance')
            performance_logger.info(
                f"Performance - {operation} on {db_name}: {duration:.3f}s")

            if duration > 1.0:
                performance_logger.warning(
                    f"Slow operation detected - {operation} on {db_name}: {duration:.3f}s")

        except Exception as e:
            logging.getLogger('performance').error(
                f"Error logging performance metrics: {e}")

    def cleanup_old_stats(self, max_age_hours=24):
        """Clean up old connection statistics from the in-memory store."""
        current_time = time.time()
        if current_time - self.last_cleanup > 3600:  # Clean up once per hour
            cutoff_time = current_time - (max_age_hours * 3600)
            self.connection_stats = {
                k: v for k, v in self.connection_stats.items()
                if v.get('timestamp', 0) > cutoff_time
            }
            self.last_cleanup = current_time


# --- Global Monitor Instance and Helper Functions ---
db_monitor = DatabaseMonitor()


@contextmanager
def monitored_database_operation(operation_name, db_name="unknown"):
    """Context manager to monitor database operations with timing and logging."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        db_monitor.log_performance_metrics(operation_name, duration, db_name)


def log_database_status():
    """Logs the status of all relevant database connections."""
    try:
        if hasattr(current_app, 'config') and 'PROJECT_DB' in current_app.config:
            main_db = current_app.config['PROJECT_DB']
            if hasattr(main_db, 'db_engine'):
                db_monitor.log_connection_pool_status(
                    main_db.db_engine, "chatbot_main")

        db_monitor.log_memory_usage()
        db_monitor.cleanup_old_stats()

    except Exception as e:
        logging.getLogger('database').error(
            f"Error in log_database_status: {e}")
