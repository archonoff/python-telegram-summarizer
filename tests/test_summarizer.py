import pytest

from summarizer import extract_ids_from_telegram_url, get_end_message_id


class TestGetEndMessageId:

    def test_get_end_message_id_success(self):
        """Test https://t.me/channel_name/123/456"""
        end_url = "https://t.me/channel_name/123/456"
        channel_name = "channel_name"
        thread_id = 123
        result = get_end_message_id(end_url, channel_name, thread_id)
        assert result == 456

    def test_get_end_message_id_different_channel(self):
        """Test different channel"""
        end_url = "https://t.me/different_channel/123/456"
        channel_name = "channel_name"
        thread_id = 123
        with pytest.raises(ValueError) as excinfo:
            get_end_message_id(end_url, channel_name, thread_id)
        assert "Links must belong to the same channel" in str(excinfo.value)

    def test_get_end_message_id_different_thread(self):
        """Test different thread"""
        end_url = "https://t.me/channel_name/999/456"
        channel_name = "channel_name"
        thread_id = 123
        with pytest.raises(ValueError) as excinfo:
            get_end_message_id(end_url, channel_name, thread_id)
        assert "Links must belong to the same thread" in str(excinfo.value)

    def test_get_end_message_id_no_thread_id(self):
        """Test no thread_id"""
        end_url = "https://t.me/channel_name/456"
        channel_name = "channel_name"
        thread_id = None
        result = get_end_message_id(end_url, channel_name, thread_id)
        assert result == 456

    @pytest.mark.parametrize("url, expected_channel, expected_thread, expected_msg", [
        ("https://t.me/channel_name/456", "channel_name", None, 456),
        ("https://t.me/channel_name/123/456", "channel_name", 123, 456),
        ("http://t.me/my_channel/789", "my_channel", None, 789),
    ])
    def test_extract_ids_from_telegram_url(self, url, expected_channel, expected_thread, expected_msg):
        """Test various URL formats"""
        channel, thread, msg = extract_ids_from_telegram_url(url)
        assert channel == expected_channel
        assert thread == expected_thread
        assert msg == expected_msg


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
