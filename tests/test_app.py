import os
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.app import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_clone_video_success():
    # We patch background_clone_and_send to prevent real cloning and webhook requests in tests
    with patch("src.app.background_clone_and_send") as mock_background_task:
        response = client.post("/api/clone", json={
            "url": "https://instagram.com/reel/123",
            "webhook_url": "https://test-webhook.example.com"
        })
        
    mock_background_task.assert_called_once()
    args, kwargs = mock_background_task.call_args
    assert args[0] == "https://instagram.com/reel/123"
    assert args[1] is None
    assert args[2] == "https://test-webhook.example.com"
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    assert "iniciada com sucesso" in response.json()["message"]
    assert response.json()["url"] == "https://instagram.com/reel/123"
    assert response.json()["webhook_target"] == "https://test-webhook.example.com"


def test_clone_video_value_error():
    response = client.post("/api/clone", json={})
    assert response.status_code == 400


@patch("src.app.httpx.post")
def test_send_video_to_n8n_success(mock_post, tmp_path):
    from src.app import send_video_to_n8n
    
    # Create a dummy video file
    dummy_video = tmp_path / "test_video.mp4"
    dummy_video.write_bytes(b"dummy video content")
    
    # Configure mock response
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.text = "OK"
    
    send_video_to_n8n(str(dummy_video), "https://instagram.com/reel/123", "https://test-webhook.example.com")
    
    # Verify httpx.post was called
    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    assert call_args[0] == "https://test-webhook.example.com"
    payload = call_kwargs["json"]
    assert payload["status"] == "success"
    assert payload["url"] == "https://instagram.com/reel/123"
    assert payload["file_name"] == "test_video.mp4"
    assert payload["video_base64"] == "ZHVtbXkgdmlkZW8gY29udGVudA=="


@patch("src.app.httpx.post")
def test_send_video_to_n8n_file_not_found(mock_post):
    from src.app import send_video_to_n8n
    
    # Configure mock response for the failure post
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.text = "OK"
    
    send_video_to_n8n("nonexistent_video.mp4", "https://instagram.com/reel/123", "https://test-webhook.example.com")
    
    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    assert call_args[0] == "https://test-webhook.example.com"
    payload = call_kwargs["json"]
    assert payload["status"] == "failed"
    assert "nonexistent_video.mp4" in payload["error"]
