import os
import json
import logging
from cryptography.fernet import Fernet
from .chatbot_service import get_chatbot_db
from ..utils.exceptions import ServiceException
from ..constants import LLM_NAMES

logger = logging.getLogger(__name__)

# Encryption key for API keys - ensure stable across restarts
_CIPHER = None

def _get_or_create_encryption_key():
    """
    Use a single environment-provided key for encryption/decryption.

    - Reads from FERNET_KEY only.
    - Does not use or persist any DB-stored master key.
    - If FERNET_KEY is missing, an ephemeral key is generated (decrypt of
      previously encrypted values will fail in that case) and a clear
      error is logged to prompt configuration.
    """
    env_key = os.getenv('FERNET_KEY')
    if env_key:
        try:
            return env_key.encode()
        except Exception as e:
            logger.error(f"Invalid FERNET_KEY in environment: {e}")
            # fall through to ephemeral
    logger.error("FERNET_KEY not set; using ephemeral key. Set FERNET_KEY in environment for stable encryption.")
    return Fernet.generate_key()

def _get_cipher():
    global _CIPHER
    if _CIPHER is None:
        _CIPHER = Fernet(_get_or_create_encryption_key())
    return _CIPHER


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for secure storage."""
    if not api_key:
        return ""
    try:
        encrypted_key = _get_cipher().encrypt(api_key.encode())
        return encrypted_key.decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {str(e)}")
        raise ServiceException("Failed to encrypt API key", 500)


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key for use."""
    if not encrypted_key:
        return ""
    try:
        decrypted_key = _get_cipher().decrypt(encrypted_key.encode())
        return decrypted_key.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {str(e)}")
        raise ServiceException("Failed to decrypt API key", 500)


def mask_key(api_key: str) -> str:
    """Return a masked preview like abc***xyz without exposing the full key."""
    if not api_key:
        return ""
    try:
        if len(api_key) <= 6:
            return "***"
        return f"{api_key[:3]}***{api_key[-3:]}"
    except Exception:
        return "***"


def get_env_api_key_status_service():
    """Check which LLM providers have API keys configured in .env."""
    status = {}
    
    for provider in LLM_NAMES:
        provider_lower = provider.lower()
        env_key_name = f"{provider_lower}_api_key".upper()
        has_key = bool(os.getenv(env_key_name))
        status[provider] = {
            "has_env_key": has_key,
            "env_key_name": env_key_name
        }
    
    return {
        "status": "success",
        "env_api_keys": status
    }


def get_ai_settings_service(llm_name: str | None = None):
    """Get current global AI settings. If llm_name is provided, return values for that LLM."""
    try:
        db = get_chatbot_db()
        
        # Get global API settings from api_settings table
        global_settings = {}
        try:
            with db.db_engine.connect() as connection:
                result = connection.execute(
                    db.api_settings_table.select()
                )
                for row in result:
                    global_settings[row.setting_key] = row.setting_value
        except Exception as e:
            logger.warning(f"Could not fetch global API settings: {str(e)}")
        
        # Get environment API key status
        env_status = get_env_api_key_status_service()
        
        # Determine current settings
        current_llm = (llm_name or global_settings.get('default_llm', 'COHERE')).upper()
        api_key_source = global_settings.get(f'default_llm_key_source_{current_llm}', 'ENV')
        
        # If using global key, compute masked preview
        global_api_key_masked = ""
        if global_settings.get(f'encrypted_api_key_{current_llm}'):
            try:
                decrypted = decrypt_api_key(global_settings[f'encrypted_api_key_{current_llm}'])
                global_api_key_masked = mask_key(decrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt global API key: {str(e)}")
        
        return {
            "status": "success",
            "settings": {
                "llm_name": current_llm,
                "api_key_source": api_key_source.lower(),
                "global_api_key_masked": global_api_key_masked,
                "has_env_key": env_status["env_api_keys"].get(current_llm, {}).get("has_env_key", False)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting AI settings: {str(e)}")
        raise ServiceException("Failed to get AI settings", 500)


def update_ai_settings_service(data):
    """Update global AI settings."""
    try:
        logger.info(f"Updating AI settings with data: {data}")
        db = get_chatbot_db()
        
        llm_name = data.get('llm_name', 'COHERE')
        api_key_source = data.get('api_key_source', 'env')
        global_api_key = data.get('global_api_key', '')
        
        logger.info(f"Parsed settings - LLM: {llm_name}, Source: {api_key_source}, Has API Key: {bool(global_api_key)}")
        
        # Validate input
        if llm_name not in LLM_NAMES:
            raise ServiceException(f"Invalid LLM provider: {llm_name}", 400)
        
        if api_key_source not in ['env', 'global', 'local']:
            raise ServiceException(f"Invalid API key source: {api_key_source}", 400)
        
        # If switching to GLOBAL without providing a key, allow if a key already exists
        if api_key_source == 'global' and not global_api_key.strip():
            # Check if an encrypted key already exists for this LLM
            existing = get_ai_settings_service(llm_name=llm_name)
            # After masking change, look for masked field
            existing_masked = existing.get('settings', {}).get('global_api_key_masked')
            if not existing_masked:
                raise ServiceException("Global API key is required when using global source", 400)
        
        # Update api_settings table using upsert
        with db.db_engine.begin() as connection:
            from uuid import uuid4
            
            def upsert_setting(setting_key: str, setting_value: str):
                """Helper function to upsert a setting"""
                # Try to update first
                result = connection.execute(
                    db.api_settings_table.update()
                    .where(db.api_settings_table.c.setting_key == setting_key)
                    .values(setting_value=setting_value)
                )
                
                # If no rows were updated, insert new row
                if result.rowcount == 0:
                    connection.execute(
                        db.api_settings_table.insert().values(
                            setting_key=setting_key,
                            setting_value=setting_value
                        )
                    )
            
            # Upsert settings (always record current default and per-LLM source)
            upsert_setting('default_llm', llm_name)
            upsert_setting(f'default_llm_key_source_{llm_name}', api_key_source.upper())
            
            # If using global key, encrypt and store it
            if api_key_source == 'global' and global_api_key:
                encrypted_key = encrypt_api_key(global_api_key)
                api_key_settings_key = f'encrypted_api_key_{llm_name}'
                upsert_setting(api_key_settings_key, encrypted_key)
            # For LOCAL, we only set the source here; local key is stored via chatbot endpoint
        
        return {
            "status": "success",
            "message": "AI settings updated successfully"
        }
        
    except ServiceException:
        raise
    except Exception as e:
        logger.error(f"Error updating AI settings: {str(e)}")
        raise ServiceException("Failed to update AI settings", 500)


def get_chatbot_ai_settings_service(chatbot_id, llm_name: str | None = None):
    """Get AI settings for a specific chatbot. If llm_name is provided, source is resolved for that LLM."""
    try:
        db = get_chatbot_db()
        
        # Get chatbot info
        chatbot = db.get_chatbot(chatbot_id)
        if not chatbot:
            raise ServiceException("Chatbot not found", 404)
        
        # Get LLM key settings from chatbots table
        llm_key_settings = chatbot.get('llm_key_settings')
        local_settings = {}
        
        if llm_key_settings:
            try:
                local_settings = json.loads(llm_key_settings)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in llm_key_settings for chatbot {chatbot_id}")
        
        # Determine effective source using api_settings overrides
        effective_llm = (llm_name or chatbot.get('current_llm_name', 'COHERE')).upper()
        global_settings = {}
        try:
            with db.db_engine.connect() as connection:
                result = connection.execute(db.api_settings_table.select())
                for row in result:
                    global_settings[row.setting_key] = row.setting_value
        except Exception:
            pass

        per_llm_source = global_settings.get(f'default_llm_key_source_{effective_llm}')
        global_key_enc = global_settings.get(f'encrypted_api_key_{effective_llm}')
        chatbot_local_enc = global_settings.get(f'chatbot:{chatbot_id}:encrypted_api_key:{effective_llm}')

        # Fallback to chatbots.llm_key_settings for local if not found in api_settings
        if not chatbot_local_enc and local_settings.get('api_key'):
            chatbot_local_enc = local_settings.get('api_key')

        # Derive masked previews
        local_masked = ""
        if chatbot_local_enc:
            try:
                dec_local = decrypt_api_key(chatbot_local_enc)
                local_masked = mask_key(dec_local)
            except Exception:
                # If decrypt fails (unexpected format), still show generic mask
                local_masked = "***"

        global_masked = ""
        if global_key_enc:
            try:
                global_masked = mask_key(decrypt_api_key(global_key_enc))
            except Exception:
                global_masked = "***"

        resolved_source = (per_llm_source or local_settings.get('api_key_source') or 'ENV').lower()

        return {
            "status": "success",
            "chatbot_id": chatbot_id,
            "settings": {
                "llm_name": effective_llm,
                "api_key_source": resolved_source,
                "local_api_key_masked": local_masked,
                "global_api_key_masked": global_masked,
                "has_env_key": get_env_api_key_status_service()["env_api_keys"].get(
                    effective_llm, {}
                ).get("has_env_key", False)
            }
        }
        
    except ServiceException:
        raise
    except Exception as e:
        logger.error(f"Error getting chatbot AI settings: {str(e)}")
        raise ServiceException("Failed to get chatbot AI settings", 500)


def update_chatbot_ai_settings_service(chatbot_id, data):
    """Update AI settings for a specific chatbot."""
    try:
        db = get_chatbot_db()
        
        # Get chatbot info
        chatbot = db.get_chatbot(chatbot_id)
        if not chatbot:
            raise ServiceException("Chatbot not found", 404)
        
        llm_name = (data.get('llm_name') or chatbot.get('current_llm_name') or 'COHERE').upper()
        api_key_source = data.get('api_key_source', 'env')
        local_api_key = data.get('local_api_key', '')
        
        # Validate input
        if api_key_source not in ['env', 'global', 'local']:
            raise ServiceException(f"Invalid API key source: {api_key_source}", 400)
        
        # Allow switching to LOCAL without immediately providing a key
        # If local_api_key is provided, we'll store it; otherwise we'll just flip the source
        
        # Prepare LLM key settings (still store on chatbot row for compatibility)
        llm_key_settings = {
            "api_key_source": api_key_source
        }
        
        if api_key_source == 'local' and local_api_key:
            llm_key_settings["api_key"] = encrypt_api_key(local_api_key)
        
        # Update chatbots table
        db.update_chatbot(
            chatbot_id=chatbot_id,
            llm_key_settings=json.dumps(llm_key_settings)
        )

        # Also persist per-chatbot LOCAL key and record per-LLM source as LOCAL
        with db.db_engine.begin() as connection:
            def upsert_setting(setting_key: str, setting_value: str):
                result = connection.execute(
                    db.api_settings_table.update()
                    .where(db.api_settings_table.c.setting_key == setting_key)
                    .values(setting_value=setting_value)
                )
                if result.rowcount == 0:
                    connection.execute(
                        db.api_settings_table.insert().values(
                            setting_key=setting_key,
                            setting_value=setting_value
                        )
                    )

            # For LOCAL: mark per-LLM source and store encrypted local key for this chatbot
            if api_key_source == 'local':
                upsert_setting(f'default_llm_key_source_{llm_name}', 'LOCAL')
                if local_api_key:
                    enc = encrypt_api_key(local_api_key)
                    upsert_setting(f'chatbot:{chatbot_id}:encrypted_api_key:{llm_name}', enc)
        
        return {
            "status": "success",
            "message": "Chatbot AI settings updated successfully"
        }
        
    except ServiceException:
        raise
    except Exception as e:
        logger.error(f"Error updating chatbot AI settings: {str(e)}")
        raise ServiceException("Failed to update chatbot AI settings", 500)


def set_local_api_key_for_chatbot(chatbot_id: str, llm_name: str, api_key: str):
    """Set a local API key for a specific chatbot and LLM in the global settings table."""
    try:
        db = get_chatbot_db()
        
        with db.db_engine.begin() as connection:
            def upsert_setting(setting_key: str, setting_value: str):
                """Helper function to upsert a setting"""
                result = connection.execute(
                    db.api_settings_table.update()
                    .where(db.api_settings_table.c.setting_key == setting_key)
                    .values(setting_value=setting_value)
                )
                
                if result.rowcount == 0:
                    connection.execute(
                        db.api_settings_table.insert().values(
                            setting_key=setting_key,
                            setting_value=setting_value
                        )
                    )
            
            # Encrypt and store the local API key
            encrypted_key = encrypt_api_key(api_key)
            local_key_name = f'chatbot:{chatbot_id}:encrypted_api_key:{llm_name}'
            upsert_setting(local_key_name, encrypted_key)
            
        return {"status": "success", "message": "Local API key set successfully"}
        
    except Exception as e:
        logger.error(f"Error setting local API key: {str(e)}")
        raise ServiceException("Failed to set local API key", 500)


def get_global_api_key_plain(llm_name: str) -> str:
    """Return the decrypted GLOBAL API key for the given LLM.
    This is intended for explicit copy-to-clipboard UX and should not be used to render in UI.
    """
    try:
        db = get_chatbot_db()
        with db.db_engine.connect() as connection:
            row = connection.execute(
                db.api_settings_table.select().where(
                    db.api_settings_table.c.setting_key == f'encrypted_api_key_{llm_name.upper()}'
                )
            ).fetchone()
            if not row or not row._mapping.get('setting_value'):
                return ""
            return decrypt_api_key(row._mapping['setting_value'])
    except Exception as e:
        logger.error(f"Error fetching global api key: {e}")
        raise ServiceException("Failed to read global API key", 500)


def get_local_api_key_plain(chatbot_id: str, llm_name: str) -> str:
    """Return the decrypted LOCAL API key for the given chatbot and LLM.
    Checks api_settings override first, then falls back to chatbots.llm_key_settings.
    """
    try:
        db = get_chatbot_db()
        # Check api_settings table for per-chatbot local key
        with db.db_engine.connect() as connection:
            row = connection.execute(
                db.api_settings_table.select().where(
                    db.api_settings_table.c.setting_key == f'chatbot:{chatbot_id}:encrypted_api_key:{llm_name.upper()}'
                )
            ).fetchone()
            if row and row._mapping.get('setting_value'):
                return decrypt_api_key(row._mapping['setting_value'])

        # Fallback: read chatbots.llm_key_settings JSON
        chatbot = db.get_chatbot(chatbot_id)
        if chatbot and chatbot.get('llm_key_settings'):
            try:
                payload = json.loads(chatbot['llm_key_settings'])
                enc = payload.get('api_key')
                if enc:
                    return decrypt_api_key(enc)
            except Exception:
                pass
        return ""
    except Exception as e:
        logger.error(f"Error fetching local api key: {e}")
        raise ServiceException("Failed to read local API key", 500)
