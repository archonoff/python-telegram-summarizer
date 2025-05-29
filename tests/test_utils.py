from unittest.mock import patch, MagicMock

import pytest

from utils import split_chat_history, ensure_dirs_exist, CACHE_DIR, SUMMARY_DIR


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

        with patch('historizer.logger') as mock_logger:
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


def test_ensure_dirs_exist():
    mock_cache_path = MagicMock()
    mock_summary_path = MagicMock()

    with patch('historizer.pathlib.Path') as mock_path:
        mock_path.side_effect = lambda x: mock_cache_path if x == CACHE_DIR else mock_summary_path

        ensure_dirs_exist()

        mock_path.assert_any_call(CACHE_DIR)
        mock_path.assert_any_call(SUMMARY_DIR)

        mock_cache_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_summary_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
