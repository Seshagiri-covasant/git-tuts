import time
import psutil
from flask import current_app
from ..utils.monitoring import db_monitor


def get_system_status_service():
    """
    Returns comprehensive system status including database connections and memory usage.
    """
    # Trigger logging of current status
    db_monitor.log_memory_usage()

    main_db = current_app.config['PROJECT_DB']
    if hasattr(main_db, 'db_engine'):
        db_monitor.log_connection_pool_status(
            main_db.db_engine, "chatbot_main")

    # Clean up old stats from the monitor
    db_monitor.cleanup_old_stats()

    # Gather memory info again after logging
    process = psutil.Process()
    memory_info = process.memory_info()
    system_memory = psutil.virtual_memory()

    # Gather agent info
    agents_cache = current_app.config.get('AGENTS_CACHE', {})
    agent_count = len(agents_cache)

    status_data = {
        'timestamp': time.time(),
        'memory': {
            'process_rss_mb': memory_info.rss / 1024 / 1024,
            'process_vms_mb': memory_info.vms / 1024 / 1024,
            'process_percent': process.memory_percent(),
            'system_total_gb': system_memory.total / 1024 / 1024 / 1024,
            'system_available_gb': system_memory.available / 1024 / 1024 / 1024,
            'system_percent': system_memory.percent
        },
        'agents': {
            'active_count': agent_count,
            'agent_ids': list(agents_cache.keys())
        },
        'connection_stats': db_monitor.connection_stats
    }

    return status_data
