import asyncio
import hashlib
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from jinja2 import Template
from langchain.schema import HumanMessage
from langchain_community.chat_models import ChatOpenAI
from openai import RateLimitError

from models import UserMessage, ServiceMessage

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


CACHE_DIR = 'chat_history/cache'
SUMMARY_DIR = 'chat_history/summaries'
TODAY = datetime.now().strftime('%Y-%m-%d')


CHUNK_SUMMARY_PROMPT = (
    'Ты — опытный летописец, создающий историю сообщества «Аниме Ячейка».\n'
    'Твоя задача: проанализировать беседы в чате и выявить **значимые события и явления** в жизни сообщества.\n'
    'Фокусируйся на следующем:\n'
    '  - Конфликты и противостояния между участниками или группами\n'
    '  - Появление новых участников, изменивших динамику сообщества\n'
    '  - Мемы, шутки и локальный фольклор, ставшие частью культуры сообщества\n'
    '  - Внешние события, повлиявшие на сообщество (атаки, рейды, технические проблемы)\n'
    '  - Изменения в правилах, структуре или администрации сообщества\n\n'
    'Для каждого выявленного события укажи:\n'
    '  1. Дату или период (например, 12 мая 2022 или апрель-май 2022)\n'
    '  2. Название события (яркое, запоминающееся)\n'
    '  3. Основных участников и их роль\n'
    '  4. Описание событий (2-3 предложения)\n'
    '  5. Значение для истории сообщества\n\n'
    'Особенно внимательно отмечай следующие события, если встретишь их упоминания:\n'
    '  - «Стикерные войны» (что бы это ни значило)\n'
    '  - «Противостояние с двачерами» — конфликты с пользователями имиджборда 2ch\n'
    '  - «Нападения польских хакеров» — случаи взлома и массового спама\n'
    '  - «Чувак с бесконечными обезьянами» (что бы это ни значило)\n'
    '  - Любые другие события, которые упоминаются несколькими участниками как значимые\n\n'
    'Не ограничивайся приведенными примерами — выявляй любые события, формирующие уникальную историю и культуру «Аниме Ячейки».\n\n'
    'Проанализируй следующие сообщения из чата:\n{documents}\n\n'
    'Представь результаты анализа в виде хронологического списка событий (1., 2., 3., ...).'
)


GROUP_SUMMARY_PROMPT = (
    'Ты — историк сообщества «Аниме Ячейка», систематизирующий хронологические записи.\n'
    'Перед тобой — набор исторических заметок, описывающих различные события в жизни сообщества:\n\n{summaries}\n\n'
    'Твоя задача — объединить эти записи в **структурированный временной отрезок истории сообщества**.\n\n'
    'В своём анализе:\n'
    '1. Систематизируй описанные события в хронологическом порядке\n'
    '2. Объедини повторяющиеся или связанные события в логические группы\n'
    '3. Выдели ключевые конфликты, персонажей и мемы, появляющиеся в этом временном отрезке\n'
    '4. Определи характерные тенденции и особенности этого периода\n'
    '5. Сохрани датировку событий и их основное содержание\n\n'
    'Особое внимание удели:\n'
    '- Последовательности событий и их причинно-следственным связям\n'
    '- Конфликтам и их участникам\n'
    '- Появлению новых значимых персонажей\n'
    '- Формированию локальных мемов и традиций\n\n'
    'Твоя цель — создать промежуточную историческую сводку, которая позже станет частью полной летописи сообщества.\n'
    'Представь результат в виде хронологического списка событий с датами, названиями и кратким описанием.\n'
    f'Кстати, сегодня {TODAY}, так что смотри не залезь в будущее'
)


FINAL_SUMMARY_PROMPT = (
    'Ты — мастер исторического повествования, создающий летопись сообщества «Аниме Ячейка».\n'
    'Перед тобой — серия хронологических заметок, охватывающих разные периоды жизни сообщества:\n\n{summaries}\n\n'
    'Твоя миссия — преобразовать эти разрозненные записи в **увлекательную и целостную историю сообщества**, '
    'выделив ключевые эпохи и переломные моменты его развития.\n\n'
    'В своем повествовании:\n'
    '1. Раздели историю на 3-7 значимых эпох или периодов\n'
    '2. Для каждой эпохи придумай яркое, метафоричное название (например, «Золотой век стикеров» или «Эра великого раскола»)\n'
    '3. Определи хронологические рамки каждой эпохи\n'
    '4. Опиши характерные черты каждого периода, его атмосферу и значение\n'
    '5. Укажи ключевые события, определившие ход истории сообщества\n'
    '6. Отметь выдающихся личностей каждой эпохи и их влияние\n'
    '7. Прослеживай развитие мемов, шуток и традиций через разные периоды\n\n'
    'Особое внимание удели известным событиям в истории «Аниме Ячейки»:\n'
    '- Стикерные войны и их последствия\n'
    '- Конфликты с внешними группами (двачеры, набеги, рейды)\n'
    '- Технические потрясения (взломы, атаки хакеров)\n'
    '- Появление знаковых персонажей и ботов\n'
    '- Формирование уникальной культуры и традиций сообщества\n\n'
    'Пиши живым, увлекательным языком, как будто рассказываешь историю древней цивилизации, '
    'со своими героями, конфликтами и культурным наследием.\n\n'
    'Оформи текст следующим образом:\n'
    '=== НАЗВАНИЕ ЭПОХИ (временной период) ===\n'
    '[Общее описание эпохи, ее атмосферы и значения]\n\n'
    '1. [Дата]: [Событие] — [краткое описание]\n'
    '2. [Дата]: [Событие] — [краткое описание]\n'
    '[и так далее для каждой эпохи]\n\n'
    'В завершение истории сделай краткий эпилог о том, какой путь прошло сообщество и что делает «Аниме Ячейку» особенным культурным феноменом.\n'
    f'Кстати, сегодня {TODAY}, так что смотри не залезь в будущее'
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


class Historizer:
    chunk_size: int
    messages_dict = {}

    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size
        ensure_dirs_exist()

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

    def get_chunk_hash(self, chunk: list) -> str:
        # Use first and last messages to identify a chunk
        first_msg = chunk[0]
        last_msg = chunk[-1]
        chunk_id = f"{first_msg.id}_{last_msg.id}_{len(chunk)}"
        return hashlib.md5(chunk_id.encode()).hexdigest()

    def get_cache_path(self, chunk_hash: str) -> str:
        return os.path.join(CACHE_DIR, f"chunk_{chunk_hash}.txt")

    def is_cached(self, chunk_hash: str) -> bool:
        cache_path = self.get_cache_path(chunk_hash)
        return os.path.exists(cache_path)

    def load_from_cache(self, chunk_hash: str) -> str:
        cache_path = self.get_cache_path(chunk_hash)
        if not os.path.exists(cache_path):
            raise FileNotFoundError(f"Cache file not found: {cache_path}")

        with open(cache_path, 'r', encoding='utf-8') as f:
            data = f.read()

        return data

    def save_to_cache(self, chunk_hash: str, summary: str):
        cache_path = self.get_cache_path(chunk_hash)

        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(summary)

    async def summarize_chunk(self, chunk: list, chat_model) -> str:
        chunk_hash = self.get_chunk_hash(chunk)

        if self.is_cached(chunk_hash):
            logger.info(f'Using cached summary for chunk with hash {chunk_hash}')
            return self.load_from_cache(chunk_hash)

        logger.info(f'Summarizing chunk of size {len(chunk)} with hash {chunk_hash}')

        try:
            messages_content = [self.render_message(msg) for msg in chunk]
            content = CHUNK_SUMMARY_PROMPT.format(documents='\n\n'.join(messages_content))
            messages = [HumanMessage(content=content)]
            response = await chat_model.ainvoke(messages)
            summary = response.content

            self.save_to_cache(chunk_hash, summary)
            logger.info('Chunk summarized successfully and cached')

        except RateLimitError as e:
            error_message = str(e).lower()

            if 'too large' in error_message:
                logger.warning(f'Chunk too large for context window, splitting in half: {e}')

                middle = len(chunk) // 2
                first_half = chunk[:middle]
                second_half = chunk[middle:]

                logger.info(f'Splitting chunk of size {len(chunk)} into two chunks of sizes {len(first_half)} and {len(second_half)}')

                first_summary = await self.summarize_chunk(first_half, chat_model)
                second_summary = await self.summarize_chunk(second_half, chat_model)

                summary = f"{first_summary}\n\n{second_summary}"

                self.save_to_cache(chunk_hash, summary)

                logger.info('Split chunks summarized successfully and combined result cached')
            else:
                logger.error(f'Error during chunk summarization: {e}')
                raise

        return summary

    async def summarize_final(self, summarized_chunks: list, chat_model) -> str:
        logger.info('Summarizing final history from summarized chunks')
        summaries_content = '\n\n'.join(summarized_chunks)
        content = FINAL_SUMMARY_PROMPT.format(summaries=summaries_content)
        messages = [HumanMessage(content=content)]
        response = await chat_model.ainvoke(messages)
        final_summary = response.content

        final_summary_path = os.path.join(SUMMARY_DIR, "final_summary.txt")
        with open(final_summary_path, 'w', encoding='utf-8') as f:
            f.write(final_summary)

        logger.info(f'Final summary created and saved to {final_summary_path}')
        return final_summary

    async def summarize_final_in_groups(self, summarized_chunks: list, group_chat_model, final_chat_model, group_size=100) -> str:
        logger.info('Summarizing final history from summarized chunks in groups')

        groups = [summarized_chunks[i:i + group_size] for i in range(0, len(summarized_chunks), group_size)]

        logger.info(f'Split {len(summarized_chunks)} chunks into {len(groups)} groups')

        group_summaries = []
        for i, group in enumerate(groups):
            logger.info(f'Summarizing group {i + 1}/{len(groups)}')
            group_summaries_content = '\n\n'.join(group)
            group_content = GROUP_SUMMARY_PROMPT.format(summaries=group_summaries_content)
            group_messages = [HumanMessage(content=group_content)]

            group_response = await group_chat_model.ainvoke(group_messages)
            group_summary = group_response.content
            group_summaries.append(group_summary)

            group_summary_path = os.path.join(SUMMARY_DIR, f"group_summary_{i + 1}.txt")
            with open(group_summary_path, 'w', encoding='utf-8') as f:
                f.write(group_summary)

        final_summaries_content = '\n\n'.join(group_summaries)
        final_content = FINAL_SUMMARY_PROMPT.format(summaries=final_summaries_content)
        final_messages = [HumanMessage(content=final_content)]

        final_response = await final_chat_model.ainvoke(final_messages)
        final_summary = final_response.content

        final_summary_path = os.path.join(SUMMARY_DIR, "final_summary.txt")
        with open(final_summary_path, 'w', encoding='utf-8') as f:
            f.write(final_summary)

        logger.info(f'Final summary created and saved to {final_summary_path}')
        return final_summary

    async def run(self):
        chat_history = await load_chat_history('chat_history/result.json')
        chat_history_chunks = await split_chat_history(chat_history.messages, chunk_size=self.chunk_size)

        chunks_chat_model = ChatOpenAI(model='gpt-4.1-nano', temperature=0.3, api_key=OPENAI_API_KEY)
        groups_chat_model = ChatOpenAI(model='gpt-4.1-mini', temperature=0.3, api_key=OPENAI_API_KEY)
        final_chat_model = ChatOpenAI(model='gpt-4.1', temperature=0.3, api_key=OPENAI_API_KEY)
        logger.info('Chat models initialized')

        summarized_chunks = []
        for i, chunk in enumerate(chat_history_chunks):
            logger.info(f'Summarizing chunk {i + 1}/{len(chat_history_chunks)}')
            chunk_summary = await self.summarize_chunk(chunk, chunks_chat_model)
            summarized_chunks.append(chunk_summary)

        final_summary = await self.summarize_final_in_groups(summarized_chunks, groups_chat_model, final_chat_model, 70)

        logger.info('All processing completed successfully')
        return final_summary


if __name__ == '__main__':
    historizer = Historizer(chunk_size=6000)
    asyncio.run(historizer.run())
