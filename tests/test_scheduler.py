import pytest
from src.scheduler import calculate_batch_timestamps


def test_calculate_batch_timestamps():
    timestamps = calculate_batch_timestamps(
        count=3,
        start_time_iso="2026-07-25T12:00:00+00:00",
        interval_hours=3
    )
    assert len(timestamps) == 3
    assert "2026-07-25T12:00:00" in timestamps[0]
    assert "2026-07-25T15:00:00" in timestamps[1]
    assert "2026-07-25T18:00:00" in timestamps[2]


def test_safe_posting_window_adjustment():
    from datetime import datetime, timezone
    from src.scheduler import adjust_to_safe_posting_window

    # 02:00 AM UTC-3 is 05:00 UTC -> should bump to 06:00 AM UTC-3 (09:00 UTC)
    late_night_utc = datetime(2026, 7, 25, 5, 0, tzinfo=timezone.utc)
    safe_dt = adjust_to_safe_posting_window(late_night_utc, timezone_offset_hours=-3)

    local_hour = (safe_dt.hour - 3) % 24
    assert local_hour == 6

    # 14:00 PM UTC-3 (17:00 UTC) -> stays 14:00 UTC-3 (17:00 UTC)
    daytime_utc = datetime(2026, 7, 25, 17, 0, tzinfo=timezone.utc)
    safe_dt_day = adjust_to_safe_posting_window(daytime_utc, timezone_offset_hours=-3)
    assert safe_dt_day == daytime_utc

    # 22:00 PM UTC-3 (01:00 UTC next day) -> bumps to 06:00 AM UTC-3 next day
    night_utc = datetime(2026, 7, 26, 1, 0, tzinfo=timezone.utc)
    safe_dt_night = adjust_to_safe_posting_window(night_utc, timezone_offset_hours=-3)
    local_hour_night = (safe_dt_night.hour - 3) % 24
    assert local_hour_night == 6


def test_early_publish_and_queue_shift_scenario(tmp_path, monkeypatch):
    import uuid
    from src.database import VideoRepository
    from src.scheduler import process_due_scheduled_jobs

    db_file = str(tmp_path / "sched.db")
    repo = VideoRepository(db_file)
    repo.ensure_schema()
    user = repo.create_user(
        email=f"shift_{uuid.uuid4()}@test.com",
        password_hash="hash",
        api_key=f"key_{uuid.uuid4()}"
    )
    repo.update_user_instagram_credentials(user["id"], "ig_123", "token_123")

    # Job 1 scheduled for 11:00
    job1 = repo.create_job(user_id=user["id"], url="https://instagram.com/reel/111/")
    repo.update_job(job1["id"], status="completed", output_path="https://s3/out1.mp4")
    repo.update_job_schedule(job1["id"], caption="Job 1", scheduled_at="2026-07-25T11:00:00+00:00", share_to_feed=0)

    # Job 2 scheduled for 15:00
    job2 = repo.create_job(user_id=user["id"], url="https://instagram.com/reel/222/")
    repo.update_job(job2["id"], status="completed", output_path="https://s3/out2.mp4")
    repo.update_job_schedule(job2["id"], caption="Job 2", scheduled_at="2026-07-25T15:00:00+00:00", share_to_feed=0)

    # User posts Job 1 early at 09:00 via "Postar Agora"
    repo.mark_job_posted(job1["id"])
    repo.shift_schedule_queue_after_posting(user["id"], "2026-07-25T11:00:00+00:00")

    # Verify Job 1 state
    j1 = repo.get_job(job1["id"])
    assert j1["status"] == "completed"
    assert j1["posted_at"] is not None
    assert j1["scheduled_at"] is None

    # Verify Job 2 schedule shifted to 11:00
    j2 = repo.get_job(job2["id"])
    assert j2["status"] == "scheduled"
    assert j2["scheduled_at"] == "2026-07-25T11:00:00+00:00"

    # Mock InstagramPublisher to verify process_due_scheduled_jobs publishes Job 2 and NOT Job 1
    published_jobs = []
    class MockPublisher:
        def publish_reel(self, video_url, caption, instagram_account_id, access_token, share_to_feed=False):
            published_jobs.append({"video_url": video_url, "caption": caption})
            return {"id": "ig_media_123"}

    monkeypatch.setattr("src.instagram_publisher.InstagramPublisher", MockPublisher)

    # Simulate scheduler running at 11:00
    count = process_due_scheduled_jobs(repo)
    assert count == 1
    assert len(published_jobs) == 1
    assert published_jobs[0]["video_url"] == "https://s3/out2.mp4"
    assert published_jobs[0]["caption"] == "Job 2"

    # Verify Job 2 is now posted
    j2_posted = repo.get_job(job2["id"])
    assert j2_posted["status"] == "completed"
    assert j2_posted["posted_at"] is not None
    assert j2_posted["scheduled_at"] is None
