from unittest.mock import patch, MagicMock

import pytest

from utils import split_chat_history, ensure_dir_exist


class TestSplitChatHistory:
    @pytest.mark.asyncio
    async def test_split_chat_history_empty_list(self):
        """Test empty list"""
        result = await split_chat_history([])
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_split_chat_history_single_chunk(self):
        """Test a small chunk"""
        test_list = list(range(100))
        result = await split_chat_history(test_list, chunk_size=1000)
        assert len(result) == 1
        assert result[0] == test_list

    @pytest.mark.asyncio
    async def test_split_chat_history_multiple_chunks(self):
        """Test basic splitting"""
        test_list = list(range(25))
        chunk_size = 10
        result = await split_chat_history(test_list, chunk_size=chunk_size)

        # 3 chunks: [0-9], [10-19], [20-24]
        assert len(result) == 3
        assert result[0] == test_list[0:10]
        assert result[1] == test_list[10:20]
        assert result[2] == test_list[20:]

    @pytest.mark.asyncio
    async def test_split_chat_history_exact_chunks(self):
        """Test border case"""
        test_list = list(range(20))
        chunk_size = 10
        result = await split_chat_history(test_list, chunk_size=chunk_size)

        assert len(result) == 2
        assert result[0] == test_list[0:10]
        assert result[1] == test_list[10:20]

    @pytest.mark.asyncio
    async def test_split_chat_history_logging(self):
        """Test logging"""
        test_list = list(range(10))
        chunk_size = 5

        with patch('utils.logger') as mock_logger:
            await split_chat_history(test_list, chunk_size=chunk_size)
            assert mock_logger.info.call_count == 2
            mock_logger.info.assert_any_call(f'Splitting chat history into chunks of size {chunk_size}')

    @pytest.mark.asyncio
    async def test_split_chat_history_default_chunk_size(self):
        """Test default chunk size"""
        test_list = list(range(20000))
        default_chunk_size = 10000

        result = await split_chat_history(test_list)
        assert len(result) == 2
        assert len(result[0]) == default_chunk_size
        assert len(result[1]) == len(test_list) - default_chunk_size


def test_ensure_dir_exist():
    mock_path = MagicMock()
    path = 'path'

    with patch('utils.pathlib.Path') as mock:
        mock.return_value = mock_path
        ensure_dir_exist(path)
        mock.assert_any_call(path)
        mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
