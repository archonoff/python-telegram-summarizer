import hashlib
from unittest.mock import patch, MagicMock

import pytest

from historizer import Historizer


@pytest.fixture
def historizer():
    return Historizer()


def test_get_chunk_hash_single_message(historizer):
    msg = MagicMock()
    msg.id = 123

    chunk = [msg]
    chunk_id = f"{msg.id}_{msg.id}_{len(chunk)}"
    expected_hash = hashlib.md5(chunk_id.encode()).hexdigest()

    result = historizer.get_chunk_hash(chunk)

    assert result == expected_hash