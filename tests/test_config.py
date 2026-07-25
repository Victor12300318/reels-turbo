import pytest
from src.config import get_settings


def test_settings_from_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("LOCAL_VIDEOS_DIR", "C:\\local_videos")
    monkeypatch.setenv("DATA_DIR", "C:\\data")

    settings = get_settings()
    assert settings.gemini_api_key == "test-key"
    assert settings.gemini_model == "gemini-test"
    assert settings.local_videos_dir == "C:\\local_videos"
    assert settings.data_dir == "C:\\data"
