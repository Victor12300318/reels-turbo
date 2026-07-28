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


def test_admin_settings_endpoint():
    import uuid
    from src.app import get_repo
    repo = get_repo()
    admin_key = f"admin_key_{uuid.uuid4()}"
    user_key = f"user_key_{uuid.uuid4()}"
    repo.create_user(email=f"admin_{uuid.uuid4()}@test.com", password_hash="hash", api_key=admin_key, is_admin=1)
    repo.create_user(email=f"user_{uuid.uuid4()}@test.com", password_hash="hash", api_key=user_key, is_admin=0)

    # Non-admin forbidden
    res = client.get("/api/v1/admin/settings", headers={"X-API-Key": user_key})
    assert res.status_code == 403

    # Admin GET
    res = client.get("/api/v1/admin/settings", headers={"X-API-Key": admin_key})
    assert res.status_code == 200
    assert "ai_provider" in res.json()

    # Admin POST
    res = client.post(
        "/api/v1/admin/settings",
        headers={"X-API-Key": admin_key},
        json={
            "ai_provider": "openrouter",
            "openrouter_api_key": "sk-test-key",
            "openrouter_model": "openai/gpt-4o-mini"
        }
    )
    assert res.status_code == 200

    # Verify updated
    res = client.get("/api/v1/admin/settings", headers={"X-API-Key": admin_key})
    assert res.json()["ai_provider"] == "openrouter"
    assert res.json()["openrouter_api_key"] == "sk-test-key"
    assert res.json()["openrouter_model"] == "openai/gpt-4o-mini"


def test_job_schedule_update_and_cancel():
    import uuid
    from src.app import get_repo
    repo = get_repo()
    usr_key = f"usr_key_sched_{uuid.uuid4()}"
    user = repo.create_user(email=f"sched_{uuid.uuid4()}@test.com", password_hash="hash", api_key=usr_key)
    job = repo.create_job(user_id=user["id"], url="https://instagram.com/reel/999/")
    
    # Initially pending, mark scheduled
    repo.update_job_schedule(job["id"], caption="Cap", scheduled_at="2026-08-01T12:00:00Z", share_to_feed=0)

    # Test PATCH schedule
    res = client.patch(
        f"/api/v1/jobs/{job['id']}/schedule",
        headers={"X-API-Key": usr_key},
        json={"scheduled_at": "2026-08-02T15:30:00Z"}
    )
    assert res.status_code == 200
    assert res.json()["scheduled_at"] == "2026-08-02T15:30:00Z"

    updated_job = repo.get_job(job["id"])
    assert updated_job["scheduled_at"] == "2026-08-02T15:30:00Z"
    assert updated_job["status"] == "scheduled"

    # Test DELETE schedule (cancel)
    res = client.delete(
        f"/api/v1/jobs/{job['id']}/schedule",
        headers={"X-API-Key": usr_key}
    )
    assert res.status_code == 200

    cancelled_job = repo.get_job(job["id"])
    assert cancelled_job["scheduled_at"] is None
    assert cancelled_job["status"] == "completed"


def test_video_thumbnail_and_stream_endpoints(tmp_path):
    import uuid
    from src.app import get_repo
    repo = get_repo()
    usr_key = f"usr_key_vmedia_{uuid.uuid4()}"
    user = repo.create_user(email=f"vmedia_{uuid.uuid4()}@test.com", password_hash="hash", api_key=usr_key)

    frame_file = tmp_path / "frame.jpg"
    frame_file.write_bytes(b"fake_jpg_data")
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake_mp4_data")

    repo.upsert({
        "path": str(video_file),
        "filename": "test.mp4",
        "description": "Test",
        "themes": "test",
        "orientation": "portrait",
        "duration_seconds": 5.0,
        "has_face": 0,
        "frame_paths": [str(frame_file)],
    }, user_id=user["id"])

    vid = repo.get_by_path(str(video_file))
    assert vid is not None

    res_thumb = client.get(f"/api/v1/videos/{vid['id']}/thumbnail")
    assert res_thumb.status_code == 200

    res_stream = client.get(f"/api/v1/videos/{vid['id']}/stream")
    assert res_stream.status_code == 200
