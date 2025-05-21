import asyncio
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from models import ChatHistory

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


CHUNK_SUMMARY_PROMPT = (
    'Ты — историк и документатор сообщества «Аниме Ячейка».\n'
    'Твоя задача: из приведённых ниже сообщений сформировать **хронологический список** ключевых событий за период.\n'
    'Каждое событие должно содержать:\n'
    '  1. Дату или интервал (например, 2022-03-15 или март–апрель 2022).\n'
    '  2. Заголовок события (коротко).\n'
    '  3. Краткое описание (1–2 предложения).\n\n'
    'Учитывай важные эпизоды, например:\n'
    '  - «Первая и вторая стикерные войны» — массовые баталии за эксклюзивные стикеры в чате.\n'
    '  - «Война с двачерами» — конфликт с участниками из «двача».\n'
    '  - «Нападение польских хакеров» — взлом и флуд-атаки ботами.\n'
    '  - «Появление чувака с бесконечными обезьянами» — запуск мем-бота.\n\n'
    'Исходные сообщения:\n{documents}\n'
    '**Отправь результат** в виде упорядоченного списка (1., 2., 3., …).'
)
FINAL_SUMMARY_PROMPT = (
    'Ты — профессиональный историк сообщества «Аниме Ячейка».\n'
    'У тебя есть локальные сводки по хронологическим отрезкам:\n{summaries}\n\n'
    'Твоя задача: объединить эти фрагменты в структурированную **историю**, разбив её на ключевые исторические этапы.\n'
    'Для каждого этапа укажи:\n'
    '  • Название (например, «Период стикерных войн»).\n'
    '  • Временные рамки (месяц и год начала и конца).\n'
    '  • Список ключевых событий с датами и краткими описаниями.\n\n'
    'Пример формата ответа:\n'
    '=== Период стикерных войн (март 2022 – июль 2022) ===\n'
    '1. 2022-03-15: Первая стикерная война — группы X и Y начали борьбу за редкие стикеры…\n'
    '2. 2022-05-10: Вторая стикерная война — эскалация конфликта с участием…\n\n'
    '=== Эпоха польских хакеров (август 2022 – декабрь 2022) ===\n'
    '…\n\n'
    '**Отправь итоговую историю** как текст, структурированный по этапам и событиям.'
)


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


async def main():
    chat_history = await load_chat_history('chat_history/result.json')
    chat_history_chunks = await split_chat_history(chat_history, chunk_size=10000)

    chunk = chat_history_chunks[0]


if __name__ == '__main__':
    asyncio.run(main())
