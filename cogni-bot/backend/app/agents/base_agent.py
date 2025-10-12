import logging
from ..repositories.app_db_util import AppDbUtil
from ..repositories.chatbot_db_util import ChatbotDbUtil


class BaseAgent:
    def __init__(self, app_db_util: AppDbUtil, chatbot_db_util: ChatbotDbUtil = None):
        # For application DB (query execution, set by user)
        self.app_db_util = app_db_util
        # For chatbot data (defaults to chat_bot.db)
        self.chatbot_db_util = chatbot_db_util or ChatbotDbUtil()
        self.db_engine = self.app_db_util.get_db_conn() if self.app_db_util else None
        self.logger = logging.getLogger(self.__class__.__name__)
