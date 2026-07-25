from unittest.mock import MagicMock, patch
from PIL import Image
from src.gemini_client import GeminiClient


@patch("src.gemini_client.Client")
def test_analyze_text_only(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Mock response")
    mock_client_class.return_value = mock_client

    client = GeminiClient(api_key="test-key", model="gemini-test")
    result = client.analyze([], "Describe this")

    assert result == "Mock response"
    mock_client.models.generate_content.assert_called_once()


@patch("src.gemini_client.Client")
def test_analyze_with_image(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Image response")
    mock_client_class.return_value = mock_client

    client = GeminiClient(api_key="test-key", model="gemini-test")
    img = Image.new("RGB", (10, 10), color="red")
    result = client.analyze([img], "What do you see?")

    assert result == "Image response"


def test_repair_json_string():
    from src.gemini_client import _repair_json_string
    malformed_json = '{\n  "description": "This is a video\nwith some physical newlines\ninside the string.",\n  "has_face": 1\n}'
    repaired = _repair_json_string(malformed_json)
    # The physical newlines inside the string should be escaped to \n (literal backslash + n)
    # But the physical newlines separating JSON fields should NOT be changed!
    assert 'This is a video\\nwith some physical newlines\\ninside the string.' in repaired
    assert '{\n  "description"' in repaired


def test_repair_json_string_with_quotes():
    from src.gemini_client import _repair_json_string
    malformed_json = '{\n  "reason": "This video is great because of "style" and vibe.",\n  "path": "/app/video.mp4"\n}'
    repaired = _repair_json_string(malformed_json)
    # The inner quotes around "style" should be escaped to \"
    assert 'because of \\"style\\" and vibe.' in repaired
    assert '"path":' in repaired


@patch("src.gemini_client.Client")
@patch("time.sleep")  # Mock sleep so tests run instantly
def test_analyze_retry_on_transient_error(mock_sleep, mock_client_class):
    mock_client = MagicMock()
    # First call raises a transient error, second call succeeds!
    mock_response = MagicMock(text="Retry Success!")
    mock_client.models.generate_content.side_effect = [
        Exception("503 UNAVAILABLE: Model experiencing high demand"),
        mock_response,
    ]
    mock_client_class.return_value = mock_client

    client = GeminiClient(api_key="test-key", model="gemini-test")
    result = client.analyze([], "Test Retry")

    assert result == "Retry Success!"
    assert mock_client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once_with(2.0)



