import logging
import pathlib

from models import ChatHistory

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CACHE_DIR = 'chat_history/cache'
SUMMARY_DIR = 'chat_history/summaries'


def ensure_dirs_exist():
    pathlib.Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    pathlib.Path(SUMMARY_DIR).mkdir(parents=True, exist_ok=True)


async def load_chat_history(file_path: str) -> ChatHistory:
    logger.info(f'Loading chat history from {file_path}')
    with open(file_path, 'r', encoding='utf-8') as file:
        chat_history = ChatHistory.model_validate_json(file.read())
    logger.info(f'Chat history loaded: {len(chat_history.messages)} messages')
    return chat_history


async def split_chat_history(chat_history: list, chunk_size: int = 10000) -> list:
    logger.info(f'Splitting chat history into chunks of size {chunk_size}')
    chunks = [chat_history[i:i + chunk_size] for i in range(0, len(chat_history), chunk_size)]
    logger.info(f'Chat history split into {len(chunks)} chunks')
    return chunks
