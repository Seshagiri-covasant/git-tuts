import os
import logging
import json
from typing import Optional
from dotenv import load_dotenv
from langchain_core.language_models import BaseLanguageModel
from langchain_openai.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain_cohere import ChatCohere
from langchain_google_genai import ChatGoogleGenerativeAI
from anthropic import Anthropic
from .. import constants
from ..services.settings_service import decrypt_api_key
from ..services.chatbot_service import get_chatbot_db

# Ensure .env values override any existing OS env vars (e.g., stale keys)
load_dotenv(override=True)
logger = logging.getLogger(__name__)


def get_api_key_for_llm(llm_name: str, chatbot_id: Optional[str] = None) -> str:
    """
    Get API key for LLM based on the configured source (env, global, or local).
    
    Args:
        llm_name: Name of the LLM (e.g., 'COHERE', 'OPENAI')
        chatbot_id: Optional chatbot ID for local API key lookup
        
    Returns:
        API key string
    """
    try:
        db = get_chatbot_db()
        
        # Get global settings
        global_settings = {}
        try:
            with db.db_engine.connect() as connection:
                result = connection.execute(db.api_settings_table.select())
                for row in result:
                    global_settings[row.setting_key] = row.setting_value
        except Exception as e:
            logger.warning(f"Could not fetch global API settings: {str(e)}")
        
        # Determine API key source for this specific LLM
        api_key_source = global_settings.get(f'default_llm_key_source_{llm_name}', 'ENV')
        
        if api_key_source == 'ENV':
            # Use environment variable
            env_key_name = f"{llm_name.lower()}_api_key".upper()
            return os.getenv(env_key_name, '')
        
        elif api_key_source == 'GLOBAL':
            # Use global API key from database
            encrypted_key = global_settings.get(f'encrypted_api_key_{llm_name}', '')
            if encrypted_key:
                return decrypt_api_key(encrypted_key)
            return ''
        
        elif chatbot_id:
            # LOCAL flow: either explicitly selected or inferred from presence of a local key
            local_key_name = f'chatbot:{chatbot_id}:encrypted_api_key:{llm_name}'
            encrypted_key = global_settings.get(local_key_name, '')
            if encrypted_key:
                return decrypt_api_key(encrypted_key)

            # Fallback to chatbot-specific settings in chatbots table
            chatbot = db.get_chatbot(chatbot_id)
            if chatbot and chatbot.get('llm_key_settings'):
                try:
                    local_settings = json.loads(chatbot['llm_key_settings'])
                    encrypted_key = local_settings.get('api_key', '')
                    if encrypted_key:
                        return decrypt_api_key(encrypted_key)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in llm_key_settings for chatbot {chatbot_id}")
            # If we explicitly required LOCAL but no key present, fall through to ENV/GLOBAL handling above
            return ''
        
        return ''
        
    except Exception as e:
        logger.error(f"Error getting API key for {llm_name}: {str(e)}")
        return ''


def get_llm(llm_name: Optional[str] = None, temperature: float = 0.7, app_db_util=None, chatbot_db_util=None, chatbot_id: Optional[str] = None) -> BaseLanguageModel:
    """
    Dynamically fetch the LLM based on the provided model name or default configuration.

    Args:
        llm_name: Name of the LLM to use (e.g., 'AZURE', 'COHERE', 'CLAUDE', 'GEMINI', 'OPENAI')
        temperature: Temperature setting for the LLM (0.0 to 1.0)
        app_db_util: Optional database utility for app context
        chatbot_db_util: Optional database utility for chatbot context

    Returns:
        Configured language model instance

    Raises:
        ValueError: If the specified LLM is not supported or required environment variables are missing
    """
    logging.debug(
        f"get_llm called with llm_name: {llm_name}, temperature: {temperature}")
    llm: BaseLanguageModel
    model_name = (llm_name or constants.DEFAULT_LLM_NAME).upper()

    try:
        if model_name not in constants.LLM_NAMES:
            raise ValueError(f"Unsupported LLM model name: {model_name}")

        # USE the mapping for model names
        specific_model = constants.LLM_MODELS.get(model_name)

        if model_name == "AZURE":
            # Get Azure OpenAI configuration from environment variables
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_version = os.getenv(
                "AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

            # Validate required environment variables
            if not all([api_key, endpoint]):
                missing = [var for var in ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"]
                           if not os.getenv(var)]
                raise ValueError(
                    f"Missing required Azure OpenAI environment variables: {', '.join(missing)}")

            logging.info(
                f"Initializing Azure OpenAI with GPT-4o-mini model, temperature: {temperature}")

            llm = AzureChatOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version,
                azure_deployment=specific_model,
                temperature=temperature,
                max_tokens=4000,
                timeout=60
            )

        elif model_name == "OPENAI":
            # Get OpenAI configuration from environment variables
            api_key = get_api_key_for_llm(model_name, chatbot_id)

            if not api_key:
                raise ValueError(
                    "Missing required OpenAI API key. Please configure it in Global AI Settings.")

            logging.info(
                f"Initializing OpenAI with GPT-4o-mini model, temperature: {temperature}")

            llm = ChatOpenAI(
                api_key=api_key,
                model=specific_model,
                temperature=temperature,
                max_tokens=4000,
                timeout=60
            )

        elif model_name == "COHERE":
            api_key = get_api_key_for_llm(model_name, chatbot_id)
            masked = api_key[:4] + "***" + api_key[-4:] if isinstance(api_key, str) and len(api_key) > 8 else "(invalid/empty)"
            print(f"[LLM_FACTORY][COHERE] Loaded COHERE_API_KEY: {masked}")
            if not api_key:
                raise ValueError(
                    "Missing required Cohere API key. Please configure it in Global AI Settings.")
            logging.info(
                f"Initializing Cohere Chat LLM with temperature: {temperature}")
            llm = ChatCohere(
                model=specific_model,
                max_tokens=4000,
                temperature=temperature,
                cohere_api_key=api_key
            )

        elif model_name == "GEMINI":
            api_key = get_api_key_for_llm(model_name, chatbot_id)
            if not api_key:
                raise ValueError(
                    "Missing required Gemini API key. Please configure it in Global AI Settings.")
            logging.info(
                f"Initializing Google Gemini LLM with temperature: {temperature}")
            llm = ChatGoogleGenerativeAI(
                google_api_key=api_key,
                model=specific_model,
                temperature=temperature,
                max_output_tokens=4096
            )

        elif model_name == "CLAUDE":
            api_key = get_api_key_for_llm(model_name, chatbot_id)
            if not api_key:
                raise ValueError(
                    "Missing required Claude API key. Please configure it in Global AI Settings.")
            logging.info(
                f"Initializing Claude LLM with temperature: {temperature}")

            # Debug prints as requested: show the API key and model used
            try:
                masked = api_key[:4] + "***" + api_key[-4:] if isinstance(api_key, str) and len(api_key) > 8 else "(invalid/empty)"
                print(f"[LLM_FACTORY][CLAUDE] Loaded CLAUDE_API_KEY: {masked}")
                print(f"[LLM_FACTORY][CLAUDE] Using model: {specific_model}")
            except Exception:
                pass

            # Claude API integration using anthropic
            class ClaudeLLM:
                def __init__(self, api_key, model=specific_model, temperature=0.7):
                    self.client = Anthropic(api_key=api_key)
                    self.model = model
                    self.temperature = temperature

                def __call__(self, prompt, max_tokens=1024):
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=max_tokens,
                        temperature=self.temperature,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text if response.content else ""

                def invoke(self, prompt, max_tokens=1024):
                    return self.__call__(prompt, max_tokens=max_tokens)

            llm = ClaudeLLM(api_key=api_key, temperature=temperature)

        else:
            raise ValueError(f"Unsupported LLM model name: {model_name}")

        logging.debug(
            f"Successfully initialized LLM: {model_name} with temperature: {temperature}")
        return llm

    except Exception as e:
        logging.error(f"Error initializing {model_name} LLM: {str(e)}")
        raise
