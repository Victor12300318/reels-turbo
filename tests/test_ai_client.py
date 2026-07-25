import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from src.ai_client import OpenRouterClient, get_ai_client
from src.gemini_client import GeminiClient


def test_get_ai_client_default(tmp_path):
    from src.database import VideoRepository
    db_path = tmp_path / "test_ai.db"
    repo = VideoRepository(str(db_path))
    repo.ensure_schema()

    client = get_ai_client(repo=repo)
    assert isinstance(client, GeminiClient)


def test_get_ai_client_openrouter(tmp_path):
    from src.database import VideoRepository
    db_path = tmp_path / "test_ai.db"
    repo = VideoRepository(str(db_path))
    repo.ensure_schema()

    repo.set_system_setting("ai_provider", "openrouter")
    repo.set_system_setting("openrouter_api_key", "sk-or-v1-test")
    repo.set_system_setting("openrouter_model", "openai/gpt-4o-mini")

    client = get_ai_client(repo=repo)
    assert isinstance(client, OpenRouterClient)
    assert client.api_key == "sk-or-v1-test"
    assert client.model == "openai/gpt-4o-mini"


@patch("src.ai_client.requests.post")
def test_openrouter_client_analyze(mock_post):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"best_video": "v1.mp4"}'
                }
            }
        ]
    }
    mock_post.return_value = mock_res

    client = OpenRouterClient(api_key="sk-test-123", model="google/gemini-2.0-flash-001")
    img = Image.new("RGB", (100, 100), color="blue")
    result = client.analyze(images=[img], prompt="Which video is best?", response_schema={"type": "object"})

    assert '{"best_video": "v1.mp4"}' in result or "v1.mp4" in str(result)
    assert mock_post.called
