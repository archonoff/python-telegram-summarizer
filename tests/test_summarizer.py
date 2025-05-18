import pytest

from summarizer import extract_ids_from_telegram_url


class TestExtractIdsFromTelegramUrl:

    def test_extract_channel_and_message_id(self):
        """Test https://t.me/channel/message_id"""
        url = "https://t.me/durov/123456"

        channel, thread_id, message_id = extract_ids_from_telegram_url(url)

        assert channel == "durov"
        assert thread_id is None
        assert message_id == 123456

    def test_extract_channel_thread_and_message_id(self):
        """Test https://t.me/channel/thread_id/message_id"""
        url = "https://t.me/AnimeCellTbilisi/357929/826788"

        channel, thread_id, message_id = extract_ids_from_telegram_url(url)

        assert channel == "AnimeCellTbilisi"
        assert thread_id == 357929
        assert message_id == 826788

    def test_extract_with_http_not_https(self):
        """Test http"""
        url = "http://t.me/channel_name/123456"

        channel, thread_id, message_id = extract_ids_from_telegram_url(url)

        assert channel == "channel_name"
        assert thread_id is None
        assert message_id == 123456

    def test_channel_with_numbers(self):
        """Test numbers in channel name"""
        url = "https://t.me/channel123/123456"

        channel, thread_id, message_id = extract_ids_from_telegram_url(url)

        assert channel == "channel123"
        assert thread_id is None
        assert message_id == 123456

    def test_invalid_url_no_message_id(self):
        """Test channel name only"""
        url = "https://t.me/channel_name/"

        with pytest.raises(ValueError) as exc_info:
            extract_ids_from_telegram_url(url)

        assert "Invalid URL format" in str(exc_info.value)

    def test_invalid_url_wrong_format(self):
        """Test wrong url"""
        url = "https://telegram.org/channel_name/123456"

        with pytest.raises(ValueError) as exc_info:
            extract_ids_from_telegram_url(url)

        assert "Invalid URL format" in str(exc_info.value)

    def test_non_numeric_ids(self):
        """Test wrong ids"""
        url = "https://t.me/channel_name/abc/def"

        with pytest.raises(ValueError) as exc_info:
            extract_ids_from_telegram_url(url)

        assert "Invalid URL format" in str(exc_info.value)
