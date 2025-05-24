import asyncio
import logging
import os

from dotenv import load_dotenv
from jinja2 import Template
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

from models import ChatHistory, UserMessage, ServiceMessage

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
    'Исходные сообщения:\n{documents}\n\n'
    '**Отправь результат** в виде упорядоченного списка (1., 2., 3., ...).'
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


USER_MESSAGE_TEMPLATE = Template('''
USER MESSAGE:
{% if from_ %}{{from_}} {% endif %}
{{datetime}}{% if text %}
{{text}}{% endif %}{% if sticker_emoji %}
К этому сообщению прикреплён стикер с эмодзи {{sticker_emoji}}{% endif %}{% if photo %}
К этому сообщению прикреплено фото{% endif %}{% if reply_to.text %}
(В ответ на сообщение "{{reply_to.text|truncate(100, true, '...')}}"{% if reply_to.from_ %} от {{reply_to.from_}}{% endif %}){% endif %}{% if reactions %}
Поставленные реакции: {% for reaction in reactions %}{{reaction.emoji}} ({{reaction.count}}) {% endfor %}{% endif %}
------------------------
''')


SERVICE_MESSAGE_TEMPLATE = Template('''
SERVICE MESSAGE:
{% if datetime %}{{datetime}} {% endif %}
{% if action %}action = {{action}} {% endif %}
{% if actor %}actor = {{actor}} {% endif %}
------------------------
''')


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


class Historizer:
    chunk_size: int
    messages_dict = {}

    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size

    # todo проверить и доделать
    def render_message(self, message: UserMessage | ServiceMessage) -> str:
        self.messages_dict[message.id] = message

        if isinstance(message, UserMessage):
            reply_to = self.messages_dict.get(message.reply_to_message_id, None) if message.reply_to_message_id else None
            return USER_MESSAGE_TEMPLATE.render(
                from_=message.from_,
                datetime=message.date.strftime("%Y-%m-%d %H:%M:%S"),
                text=message.text,
                reply_to=reply_to,
                reactions=message.reactions,
                sticker_emoji=message.sticker_emoji,
                photo=message.photo,
            )
        elif isinstance(message, ServiceMessage):
            return SERVICE_MESSAGE_TEMPLATE.render(
                datetime=message.date.strftime("%Y-%m-%d %H:%M:%S"),
                action=message.action,
                actor=message.actor,
            )
        else:
            raise ValueError(f'Unknown message type: {type(message)}')

    async def summarize_chunk(self, chunk: list, chat_model) -> str:
        logger.info(f'Summarizing chunk of size {len(chunk)}')
        messages_content = [self.render_message(msg) for msg in chunk]
        content = CHUNK_SUMMARY_PROMPT.format(documents='\n\n'.join(messages_content))
        messages = [HumanMessage(content=content)]
        response = await chat_model.ainvoke(messages)
        logger.info('Chunk summarized successfully')
        return response.content

    async def run(self):
        chat_history = await load_chat_history('chat_history/result.json')
        chat_history_chunks = await split_chat_history(chat_history.messages, chunk_size=self.chunk_size)

        chat_model = ChatOpenAI(model='gpt-4.1-mini', temperature=0.3, openai_api_key=OPENAI_API_KEY)
        logger.info('Chat model initialized')

        summarized_chunks = []
        for i, chunk in enumerate(chat_history_chunks):
            logger.info(f'Summarizing chunk {i + 1}/{len(chat_history_chunks)}')
            chunk_summary = await self.summarize_chunk(chunk, chat_model)
            summarized_chunks.append(chunk_summary)
        pass


if __name__ == '__main__':
    historizer = Historizer(chunk_size=8000)
    asyncio.run(historizer.run())
