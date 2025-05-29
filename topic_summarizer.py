import asyncio
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from jinja2 import Template
from langchain.schema import HumanMessage
from langchain_community.chat_models import ChatOpenAI

from models import UserMessage, ServiceMessage
from templates import USER_MESSAGE_TEMPLATE
from utils import load_chat_history, ensure_dir_exist

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

OUTPUT_DIR = 'chat_history/topic_summaries'
TODAY = datetime.now().strftime('%Y-%m-%d')


TOPIC_SUMMARY_PROMPT = Template('''
Ты — эксперт по анализу дискуссий. Твоя задача — составить подробный отчет по обсуждению этих тем: "{% for topic in topics %}{{ topic }}{% if not loop.last %}, {% endif %}{% endfor %}".

В своем анализе:
1. Определи ключевых участников обсуждения и их позиции
2. Выдели основные аргументы и мнения по теме
3. Опиши ход дискуссии, важные моменты и повороты в обсуждении
4. Укажи, были ли достигнуты какие-то выводы или соглашения
5. Отметь наиболее эмоциональные моменты и конфликты (если были)

Твой отчет должен быть структурированным и объективным, с акцентом на фактическое содержание обсуждения.

Проанализируй следующие сообщения из чата:

{{messages}}

Пожалуйста, представь свой анализ в виде структурированного отчета по этим темам: "{% for topic in topics %}{{ topic }}{% if not loop.last %}, {% endif %}{% endfor %}"

Не делай анализ слишком большим. Старайся быть максимально информативным и точным.
Также постарайся использовать стиля общения и слэнга, который используется в самом обсуждении.
''')


class TopicSummarizer:
    def __init__(self, topics: list[str] | str):
        self.topics = topics if isinstance(topics, list) else [topics]
        ensure_dir_exist(OUTPUT_DIR)

    def search_messages(self, chat_history_dict: dict[int, UserMessage]) -> dict[int, UserMessage]:
        logger.info('Searching for exact match messages...')

        matching_messages = {}
        for message_id, message in chat_history_dict.items():
            if any(topic in message.text for topic in self.topics):
                matching_messages[message_id] = message

        return matching_messages

    def search_related_messages(self, exact_match_messages_dict: dict[int, UserMessage], user_messages_dict: dict[int, UserMessage]) -> list[UserMessage]:
        logger.info('Searching for related messages...')

        target_message_ids = set(exact_match_messages_dict.keys())
        replies_from_map = {msg.reply_to_message_id: msg.id for msg in user_messages_dict.values() if msg.reply_to_message_id}
        queue = list(target_message_ids)

        while queue:
            logger.debug(f'Queue size: {len(queue)}, message_ids size: {len(target_message_ids)}')

            current_id = queue.pop()
            current_message = user_messages_dict[current_id]

            # Check replies to
            if (current_message.reply_to_message_id
                    and current_message.reply_to_message_id not in target_message_ids
                    and current_message.reply_to_message_id in user_messages_dict):
                target_message_ids.add(current_message.reply_to_message_id)
                queue.append(current_message.reply_to_message_id)

            # Check replies from
            if current_id in replies_from_map:
                reply_from_id = replies_from_map[current_id]
                if reply_from_id not in target_message_ids:
                    target_message_ids.add(reply_from_id)
                    queue.append(reply_from_id)

        return [user_messages_dict[msg_id] for msg_id in target_message_ids]

    def search_neighboring_messages(self, related_messages: list[UserMessage], user_messages_dict: dict[int, UserMessage], time_delta) -> list[UserMessage]:
        """
        For each message in related_messages, find a time window of 1 day before and after,
        then find all messages in user_messages_dict that fall within those time windows.
        """
        logger.info('Searching for neighboring messages...')

        # Find overlapping intervals
        intervals = []
        current_start = related_messages[0].date - time_delta
        current_end = related_messages[0].date + time_delta

        for message in related_messages[1:]:
            msg_start = message.date - time_delta
            msg_end = message.date + time_delta

            if msg_start <= current_end:
                current_end = max(current_end, msg_end)
            else:
                intervals.append((current_start, current_end))
                current_start = msg_start
                current_end = msg_end

        intervals.append((current_start, current_end))

        # Find messages that fall into any interval
        neighboring_messages_ids = set()
        messages = sorted(user_messages_dict.values(), key=lambda x: x.date)
        interval_idx = 0
        msg_idx = 0

        while interval_idx < len(intervals) and msg_idx < len(messages):
            start_time, end_time = intervals[interval_idx]
            message = messages[msg_idx]

            if message.date < start_time:
                msg_idx += 1
            elif message.date > end_time:
                interval_idx += 1
            else:
                neighboring_messages_ids.add(message.id)
                msg_idx += 1

        return [user_messages_dict[msg_id] for msg_id in neighboring_messages_ids]

    def build_chat_history_dict(self, chat_history) -> dict[int, UserMessage | ServiceMessage]:
        logger.info('Building chat history dictionary...')

        chat_history_dict = {}
        for message in chat_history.messages:
            chat_history_dict[message.id] = message

        return chat_history_dict

    def render_user_message(self, message: UserMessage, full_chat_history_dict: dict[int, UserMessage | ServiceMessage]) -> str:
        reply_to = full_chat_history_dict.get(message.reply_to_message_id, None) if message.reply_to_message_id else None

        return USER_MESSAGE_TEMPLATE.render(
            from_=message.from_,
            datetime=message.date.strftime("%Y-%m-%d %H:%M:%S"),
            text=message.text,
            reply_to=reply_to,
            reactions=message.reactions,
            sticker_emoji=message.sticker_emoji,
            photo=message.photo,
        )

    async def summarize_topic(self, messages: list[str]) -> str:
        logger.info('Summarizing topic...')

        chat_model = ChatOpenAI(model='gpt-4.1-mini', temperature=0.3, api_key=OPENAI_API_KEY)

        content = TOPIC_SUMMARY_PROMPT.render(
            topics=self.topics,
            messages='\n\n'.join(messages)
        )

        messages = [HumanMessage(content=content)]
        response = await chat_model.ainvoke(messages)
        summary = response.content

        filename = f"{'_'.join(self.topics).replace(' ', '_').lower()}_{TODAY}.txt"
        output_path = os.path.join(OUTPUT_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(summary)

        logger.info(f'Topic summary created and saved to {output_path}')
        return summary

    async def run(self):
        logger.info('Starting topic summarization...')

        full_chat_history = await load_chat_history('chat_history/result.json')
        full_chat_history_dict = self.build_chat_history_dict(full_chat_history)

        user_messages_dict = {k: v for k, v in full_chat_history_dict.items() if isinstance(v, UserMessage)}

        exact_match_messages_dict = self.search_messages(user_messages_dict)
        related_messages = self.search_related_messages(exact_match_messages_dict, user_messages_dict)

        related_messages = sorted(related_messages, key=lambda msg: msg.date)

        neighboring_messages = self.search_neighboring_messages(related_messages, user_messages_dict, timedelta(minutes=40))

        rendered_messages = [self.render_user_message(msg, full_chat_history_dict) for msg in neighboring_messages]

        summary = await self.summarize_topic(rendered_messages)

        return summary


if __name__ == "__main__":
    summarizer = TopicSummarizer(['мацури', 'matsuri', 'матсури'])
    asyncio.run(summarizer.run())
