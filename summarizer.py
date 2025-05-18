import asyncio
import logging
import os

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


MESSAGE_TEMPLATE = Template('''
{% if first_name %}{{first_name}} {% endif %}{% if last_name %}{{last_name}} {% endif %} (@{{username}}), {{datetime}}:
{{text}}
{% if reply_to_text %}
(В ответ на сообщение "{{reply_to_text}}")
{% endif %}
''')


async def main():
    await client.start()
    logger.info('Authorized successfully.')

    messages = []
    messages_dict = {}
    async for message in client.iter_messages('AnimeCellTbilisi', reply_to=357929, min_id=824943, max_id=826083, reverse=True):
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
    asyncio.run(main())