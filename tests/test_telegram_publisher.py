import pytest
from unittest.mock import patch, MagicMock
from src.telegram_publisher import TelegramPublisher, TELEGRAM_MAX_CAPTION_LEN


def test_telegram_publisher_missing_token():
    pub = TelegramPublisher()
    with pytest.raises(ValueError, match="Telegram Bot Token is required"):
        pub.publish_video("video.mp4", caption="Test", bot_token="", channel_id="@testchannel")


def test_telegram_publisher_missing_channel():
    pub = TelegramPublisher()
    with pytest.raises(ValueError, match="Telegram Channel ID is required"):
        pub.publish_video("video.mp4", caption="Test", bot_token="1234:ABC", channel_id="")


@patch("src.telegram_publisher.httpx.Client")
def test_telegram_publisher_local_file(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 42}}
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_client

    test_file = tmp_path / "test_reel.mp4"
    test_file.write_bytes(b"fake video content")

    pub = TelegramPublisher()
    res = pub.publish_video(
        video_path=str(test_file),
        caption="Meu Reel Incrível!",
        bot_token="1234:ABC",
        channel_id="-100987654321",
        original_url="https://instagram.com/reel/xyz123"
    )

    assert res["ok"] is True
    assert res["result"]["message_id"] == 42
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "https://api.telegram.org/bot1234:ABC/sendVideo" in call_args[0][0]
    data = call_args[1]["data"]
    assert data["chat_id"] == "-100987654321"
    assert "Meu Reel Incrível!" in data["caption"]
    assert "https://instagram.com/reel/xyz123" in data["caption"]


@patch("src.telegram_publisher.httpx.Client")
def test_telegram_publisher_remote_url(mock_client_cls):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 99}}
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_client

    pub = TelegramPublisher()
    res = pub.publish_video(
        video_path="https://s3.example.com/videos/output.mp4",
        caption="Remoto",
        bot_token="token_test",
        channel_id="@meucanal"
    )

    assert res["ok"] is True
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    json_data = call_args[1]["json"]
    assert json_data["video"] == "https://s3.example.com/videos/output.mp4"
    assert json_data["chat_id"] == "@meucanal"


@patch("src.telegram_publisher.httpx.Client")
def test_telegram_publisher_api_error(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.text = "Bad Request: chat not found"
    mock_resp.json.return_value = {"ok": False, "description": "Bad Request: chat not found"}
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_client

    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(b"content")

    pub = TelegramPublisher()
    with pytest.raises(RuntimeError, match="Bad Request: chat not found"):
        pub.publish_video(str(test_file), bot_token="123:ABC", channel_id="@invalid")
