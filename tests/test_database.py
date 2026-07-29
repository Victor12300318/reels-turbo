import pytest
from src.database import VideoRepository


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    repo = VideoRepository(str(db_path))
    repo.ensure_schema()
    return repo


def test_upsert_and_get(repo):
    repo.upsert({
        "path": "C:\\videos\\sample.mp4",
        "filename": "sample.mp4",
        "description": "A sample video",
        "themes": "sample,demo",
        "orientation": "portrait",
        "duration_seconds": 12.5,
        "has_face": 1,
        "frame_paths": ["frame1.jpg", "frame2.jpg"],
    })
    rows = repo.get_all()
    assert len(rows) == 1
    assert rows[0]["filename"] == "sample.mp4"
    assert rows[0]["description"] == "A sample video"
    assert rows[0]["frame_paths"] == ["frame1.jpg", "frame2.jpg"]


def test_get_by_path(repo):
    repo.upsert({
        "path": "C:\\videos\\sample.mp4",
        "filename": "sample.mp4",
        "description": "A sample video",
        "themes": "",
        "orientation": "",
        "duration_seconds": 0.0,
        "has_face": 0,
        "frame_paths": [],
    })
    row = repo.get_by_path("C:\\videos\\sample.mp4")
    assert row is not None
    assert row["filename"] == "sample.mp4"
    assert row["frame_paths"] == []


def test_user_and_job_operations(repo):
    # Create user
    user = repo.create_user(email="test@example.com", password_hash="hash123", api_key="usr_key_123")
    assert user["email"] == "test@example.com"
    assert user["api_key"] == "usr_key_123"

    # Get user by email & api key
    by_email = repo.get_user_by_email("test@example.com")
    assert by_email is not None and by_email["id"] == user["id"]

    by_key = repo.get_user_by_api_key("usr_key_123")
    assert by_key is not None and by_key["id"] == user["id"]

    # Job operations
    job = repo.create_job(user_id=user["id"], url="https://instagram.com/reel/123/")
    assert job["status"] == "pending"
    assert job["user_id"] == user["id"]

    repo.update_job(job_id=job["id"], status="completed", progress=100, output_path="out.mp4")
    fetched_job = repo.get_job(job["id"])
    assert fetched_job["status"] == "completed"
    assert fetched_job["output_path"] == "out.mp4"

    user_jobs = repo.get_jobs_by_user(user["id"])
    assert len(user_jobs) == 1
    assert user_jobs[0]["id"] == job["id"]

    # Test job archiving
    repo.archive_job(job["id"])
    assert len(repo.get_jobs_by_user(user["id"])) == 0
    archived_job = repo.get_job(job["id"])
    assert archived_job["status"] == "archived"


def test_multi_tenant_video_isolation(repo):
    user1 = repo.create_user(email="u1@test.com", password_hash="hash", api_key="key1")
    user2 = repo.create_user(email="u2@test.com", password_hash="hash", api_key="key2")

    repo.upsert({"path": "v1.mp4", "filename": "v1.mp4"}, user_id=user1["id"])
    repo.upsert({"path": "v2.mp4", "filename": "v2.mp4"}, user_id=user2["id"])

    u1_videos = repo.get_all(user_id=user1["id"])
    u2_videos = repo.get_all(user_id=user2["id"])

    assert len(u1_videos) == 1
    assert u1_videos[0]["filename"] == "v1.mp4"
    assert len(u2_videos) == 1
    assert u2_videos[0]["filename"] == "v2.mp4"


def test_user_settings_and_job_scheduling(repo):
    user = repo.create_user(email="sched@test.com", password_hash="hash", api_key="key_sched")
    repo.update_user_settings(
        user_id=user["id"],
        default_caption_suffix="Siga @agufzz",
        share_to_feed=0,
        default_post_interval_hours=3
    )
    updated_user = repo.get_user_by_id(user["id"])
    assert updated_user["default_caption_suffix"] == "Siga @agufzz"
    assert updated_user["default_post_interval_hours"] == 3


def test_system_settings_operations(repo):
    # Get non-existent key with default
    assert repo.get_system_setting("ai_provider", "gemini") == "gemini"

    # Set and get system settings
    repo.set_system_setting("ai_provider", "openrouter")
    repo.set_system_setting("openrouter_api_key", "sk-or-v1-123456")
    repo.set_system_setting("openrouter_model", "openai/gpt-4o-mini")

    assert repo.get_system_setting("ai_provider") == "openrouter"
    assert repo.get_system_setting("openrouter_api_key") == "sk-or-v1-123456"

    all_settings = repo.get_all_system_settings()
    assert all_settings["ai_provider"] == "openrouter"
    assert all_settings["openrouter_model"] == "openai/gpt-4o-mini"


def test_video_usage_increment_and_insights(repo):
    user = repo.create_user(email="insights@test.com", password_hash="hash", api_key="key_insights")
    repo.upsert({
        "path": "C:\\videos\\v1.mp4",
        "filename": "v1.mp4",
        "description": "Video 1",
        "themes": "test",
        "orientation": "portrait",
        "duration_seconds": 10.0,
        "has_face": 0,
        "frame_paths": ["f1.jpg"],
    }, user_id=user["id"])
    
    video = repo.get_by_path("C:\\videos\\v1.mp4")
    assert video is not None
    repo.increment_video_usage(video["id"])
    v_updated = repo.get_video_by_id(video["id"])
    assert v_updated["usage_count"] == 1
    assert v_updated["last_used_at"] is not None

    job = repo.create_job(user_id=user["id"], url="https://instagram.com/reel/123/")
    repo.update_job_instagram_media_id(job["id"], "media_999")
    repo.upsert_media_insights(
        job_id=job["id"],
        instagram_media_id="media_999",
        views=15000,
        likes=800,
        comments=45,
        shares=120,
        reach=18000,
        engagement_score=19500.0
    )
    top_reels = repo.get_top_performing_reels(user_id=user["id"], top_k=5)
    assert len(top_reels) == 1
    assert top_reels[0]["views"] == 15000


