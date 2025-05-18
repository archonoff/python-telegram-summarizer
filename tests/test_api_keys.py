# tests/test_api_keys.py
import os
import pytest
from dotenv import load_dotenv
from openai import OpenAI
from telethon.sync import TelegramClient

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@pytest.mark.parametrize("name,value", [
    ("API_ID", API_ID),
    ("API_HASH", API_HASH),
    ("OPENAI_API_KEY", OPENAI_API_KEY),
])
def test_env_vars_exist(name, value):
    assert value, f"Variable {name} is not set"


@pytest.fixture(scope="module")
def tg_client():
    client = TelegramClient("session", int(API_ID), API_HASH)
    client.start()  # may ask for a code from Telegram on the first run
    yield client
    client.disconnect()


def test_telegram_authentication(tg_client):
    me = tg_client.get_me()
    assert me is not None, "Failed to get account information"
    assert hasattr(me, "id"), "The response is missing the id field"


def test_openai_api_key():
    client = OpenAI(api_key=OPENAI_API_KEY)
    models = client.models.list()  # Request for a list of models
    # Check that the response is a list
    assert hasattr(models, "data"), "Response does not contain .data"
    assert isinstance(models.data, list), "Expected a list of models"
