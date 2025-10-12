import os
from sqlalchemy.pool import QueuePool

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-and-unguessable-key'
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Centralized DB Pool Configurations
def get_chatbot_db_pool_config():
    return {
        'pool_size': int(os.getenv('CHATBOT_DB_POOL_SIZE', '3')),
        'max_overflow': int(os.getenv('CHATBOT_DB_MAX_OVERFLOW', '5')),
        'pool_timeout': int(os.getenv('CHATBOT_DB_POOL_TIMEOUT', '30')),
        'pool_recycle': int(os.getenv('CHATBOT_DB_POOL_RECYCLE', '3600')),
        'pool_pre_ping': os.getenv('CHATBOT_DB_POOL_PRE_PING', 'true').lower() == 'true',
        'echo': os.getenv('CHATBOT_DB_ECHO', 'false').lower() == 'true',
    }

def get_app_db_pool_config():
    return {
        'pool_size': int(os.getenv('APP_DB_POOL_SIZE', '5')),
        'max_overflow': int(os.getenv('APP_DB_MAX_OVERFLOW', '10')),
        'pool_timeout': int(os.getenv('APP_DB_POOL_TIMEOUT', '300')),
        'pool_recycle': int(os.getenv('APP_DB_POOL_RECYCLE', '3600')),
        'pool_pre_ping': os.getenv('APP_DB_POOL_PRE_PING', 'true').lower() == 'true',
        'echo': os.getenv('APP_DB_ECHO', 'false').lower() == 'true',
    }

def create_database_engine(db_url: str, pool_config: dict):
    from sqlalchemy import create_engine
    if 'sqlite' in db_url.lower():
        return create_engine(db_url, echo=pool_config.get('echo', False))
    return create_engine(
        db_url,
        poolclass=QueuePool,
        **pool_config
    )