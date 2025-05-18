import asyncio
import logging
import os
import questionary
import re

from dotenv import load_dotenv
from jinja2 import Template
from openai import OpenAI
from telethon import TelegramClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Имя сессии (создастся файл session.session)
client = TelegramClient('session', API_ID, API_HASH)


MESSAGE_TEMPLATE = Template('''
{% if first_name %}{{first_name}} {% endif %}{% if last_name %}{{last_name}} {% endif %} (@{{username}}), {{datetime}}:
{{text}}
{% if reply_to_text %}
(В ответ на сообщение "{{reply_to_text}}")
{% endif %}
''')


TG_LINK_REGEX = r'https?://t\.me/([^/]+)(?:/(\d+))?/(\d+)'


def extract_ids_from_telegram_url(url: str) -> tuple[str, int | None, int]:
    """
    channel_name, thread_id, message_id
    """

    match = re.match(TG_LINK_REGEX, url)

    if not match:
        msg = f'Invalid URL format: {url}. Expected: https://t.me/channel_name/message_id or https://t.me/channel_name/thread_id/message_id'
        logger.error(msg)
        raise ValueError(msg)

    channel_name, thread_id, message_id = match.groups()

    return channel_name, int(thread_id) if thread_id is not None else None, int(message_id)


def get_message_range_from_user() -> tuple[str, int, int | None, int | None]:
    """
    channel_name, thread_id, start_message_id, end_message_id
    """

    start_url = questionary.text('Enter the link to the first message of the discussion').ask()

    try:
        channel_name, thread_id, start_message_id = extract_ids_from_telegram_url(start_url)

        end_message_id = None

        end_url = questionary.text('Enter the link to the last message of the discussion (optional)').ask()

        if end_url:
            end_channel, end_thread, end_message = extract_ids_from_telegram_url(end_url)

            if end_channel != channel_name:
                raise ValueError(f'Links must belong to the same channel: {channel_name} ≠ {end_channel}')

            if end_thread != thread_id:
                raise ValueError(f'Links must belong to the same thread: {thread_id} ≠ {end_thread}')

            end_message_id = end_message

        return channel_name, thread_id, start_message_id, end_message_id

    except ValueError as e:
        print(f"Error: {e}")
        return get_message_range_from_user()


def summarize_text(text: str) -> str:
    system_prompt = "Ты — ассистент, который кратко и чётко резюмирует обсуждение. Выделяй основные идеи, точки зрения и выводы."
    
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{text}"},
        ],
        temperature=0.3,
    )
    
    return resp.choices[0].message.content


async def main(channel_name: str, thread_id: int | None, start_message_id: int, end_message_id: int | None):

    await client.start()
    logger.info('Authorized successfully.')

    messages = []
    messages_dict = {}
    async for message in client.iter_messages(channel_name, reply_to=thread_id, min_id=start_message_id, max_id=end_message_id, reverse=True):
        if message.text:
            messages_dict[message.id] = message.text

            reply_to_text = messages_dict.get(message.reply_to.reply_to_msg_id, None) if message.reply_to else None

            formatted_message = MESSAGE_TEMPLATE.render(
                first_name=message.sender.first_name,
                last_name=message.sender.last_name,
                username=message.sender.username,
                datetime=message.date.strftime("%Y-%m-%d %H:%M:%S"),
                text=message.text,
                reply_to_text=reply_to_text,
            )

            messages.append(formatted_message)

    if not messages:
        logger.warning('No messages found in the specified period.')
        return

    messages_combined = '\n'.join(messages)

    llm_request = f'''В телеграм чате случился срач. Ниже я приведу переписку, а ты расскажи об участниках, 
    их мнениях, кто какую позицию занимает, кто с кем спорит и о чем. А в конце напиши краткий вывод 
    и дай свою оценку, кто прав, а кто нет.\n\nПереписка:\n{messages_combined}'''

    print("\n======= Сводка =======\n")
    final_summary = summarize_text(llm_request)
    print(final_summary)


if __name__ == '__main__':
    channel_name, thread_id, start_message_id, end_message_id = get_message_range_from_user()
    asyncio.run(main(channel_name, thread_id, start_message_id, end_message_id))