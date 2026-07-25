import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


def calculate_batch_timestamps(count: int, start_time_iso: str | None = None, interval_hours: int = 3) -> list[str]:
    """
    Generates a list of ISO timestamps spaced by `interval_hours`.
    """
    if start_time_iso:
        try:
            start_dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
        except Exception:
            start_dt = datetime.now(timezone.utc)
    else:
        start_dt = datetime.now(timezone.utc)

    timestamps = []
    for i in range(count):
        t = start_dt + timedelta(hours=i * interval_hours)
        timestamps.append(t.isoformat())
    return timestamps


def process_due_scheduled_jobs(repo: Any) -> int:
    """
    Polls scheduled jobs that are due for publication and publishes them via Instagram Publisher.
    """
    due_jobs = repo.get_scheduled_jobs_due()
    if not due_jobs:
        return 0

    logger.info(f"Found {len(due_jobs)} scheduled job(s) ready for auto-posting...")
    processed_count = 0

    from src.instagram_publisher import InstagramPublisher

    for job in due_jobs:
        user = repo.get_user_by_id(job["user_id"]) or {}
        ig_account_id = user.get("instagram_account_id")
        ig_token = user.get("instagram_access_token")

        if not ig_account_id or not ig_token or not job.get("output_path"):
            logger.warning(f"Job {job['id']} skipped auto-post: missing credentials or output URL.")
            continue

        try:
            logger.info(f"Auto-publishing scheduled job {job['id']} to Instagram...")
            publisher = InstagramPublisher()
            caption = job.get("caption") or user.get("default_caption_suffix") or "Clonado com Reels Cloner AI #reels"
            share_to_feed = bool(job.get("share_to_feed", user.get("share_to_feed", 0)))

            publisher.publish_reel(
                video_url=job["output_path"],
                caption=caption,
                instagram_account_id=ig_account_id,
                access_token=ig_token,
                share_to_feed=share_to_feed
            )
            repo.mark_job_posted(job["id"])
            processed_count += 1
        except Exception as e:
            logger.error(f"Failed to publish scheduled job {job['id']}: {e}")

    return processed_count
