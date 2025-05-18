# Этот файл выдал JetBrains AI Assistant

import os
import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import InputPeerChannel, InputPeerChat
from telethon.tl.functions.messages import GetHistoryRequest
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Имя сессии (создастся файл session.session)
client = TelegramClient('session', API_ID, API_HASH)


async def fetch_messages(entity, since: datetime, until: datetime, limit=1000):
    """Собирает сообщения из чата/канала за указанный период."""
    all_messages = []
    offset_id = 0
    while True:
        history = await client(GetHistoryRequest(
            peer=entity,
            offset_id=offset_id,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))
        if not history.messages:
            break

        for msg in history.messages:
            msg_date = msg.date
            if msg_date < since:
                return all_messages
            if since <= msg_date <= until and hasattr(msg, 'message'):
                all_messages.append(msg.message)

        offset_id = history.messages[-1].id

    return all_messages


def split_chunks(messages, max_chars=15000):
    """Разбивает длинный текст на куски, чтобы не превышать лимит токенов."""
    chunks, current = [], ""
    for line in messages:
        if len(current) + len(line) > max_chars:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current:
        chunks.append(current)
    return chunks


def summarize_text(text: str) -> str:
    """Отправляет текст в OpenAI для получения краткого резюме."""
    prompt = (
        "Ты — ассистент, который кратко и чётко резюмирует обсуждение.\n\n"
        f"Текст переписки:\n{text}\n\n"
        "Выведи основные идеи, точки зрения и выводы."
    )
    resp = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=500
    )
    return resp.choices[0].message.model_dump()["content"]


async def main():
    await client.start()
    print("Клиент запущен. Введите ID чата/канала и даты.")

    # Параметры запроса
    entity_input = input("Введите username или ID канала/чата: ").strip()
    since_str = input("С какой даты (YYYY-MM-DD): ").strip()
    until_str = input("По какую дату (YYYY-MM-DD): ").strip()

    since = datetime.fromisoformat(since_str)
    until = datetime.fromisoformat(until_str)

    # Получаем entity (работает и с публичными, и с приватными чатами, если вы в них состоите)
    entity = await client.get_entity(entity_input)

    print("Собираем сообщения...")
    messages = await fetch_messages(entity, since, until)
    if not messages:
        print("Сообщений за указанный период не найдено.")
        return

    print(f"Найдено {len(messages)} сообщений. Генерируем сводку...")
    chunks = split_chunks(messages)

    summaries = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Обрабатываем часть {i}/{len(chunks)}...")
        summaries.append(summarize_text(chunk))

    final_summary = "\n\n---\n\n".join(summaries)
    print("\n======= Сводка =======\n")
    print(final_summary)


if __name__ == '__main__':
    asyncio.run(main())