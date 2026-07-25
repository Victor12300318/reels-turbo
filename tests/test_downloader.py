from unittest.mock import patch, MagicMock
from src.downloader import _sanitize_filename, download_reels


def test_sanitize_filename():
    assert _sanitize_filename("hello/world:test.mp4") == "hello_world_test.mp4"


@patch("src.downloader.YoutubeDL")
def test_download_calls_youtube_dl(mock_ydl_class):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl
    download_reels("https://instagram.com/reel/abc", "./downloads")
    mock_ydl.extract_info.assert_called_once()
