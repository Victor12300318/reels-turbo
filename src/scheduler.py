import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


def adjust_to_safe_posting_window(dt: datetime, timezone_offset_hours: int = -3) -> datetime:
    """
    Adjusts a datetime object so it falls strictly within the safe posting window
    between 06:00 AM and 21:00 PM (default timezone: UTC-3 Horário de Brasília).
    If a scheduled time falls during dead hours (21:01 to 05:59), it rolls forward to 06:00 AM.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    local_tz = timezone(timedelta(hours=timezone_offset_hours))
    local_dt = dt.astimezone(local_tz)

    if local_dt.hour < 6:
        adjusted_local = local_dt.replace(hour=6, minute=0, second=0, microsecond=0)
    elif local_dt.hour >= 21:
        adjusted_local = (local_dt + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        adjusted_local = local_dt

    return adjusted_local.astimezone(timezone.utc)


def calculate_batch_timestamps(count: int, start_time_iso: str | None = None, interval_hours: int = 3) -> list[str]:
    """
    Generates a list of ISO timestamps spaced by `interval_hours`, strictly within safe posting window.
    """
    if start_time_iso:
        try:
            start_dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
        except Exception:
            start_dt = datetime.now(timezone.utc)
    else:
        start_dt = datetime.now(timezone.utc)

    current_dt = adjust_to_safe_posting_window(start_dt)
    timestamps = []

    for i in range(count):
        if i == 0:
            slot = current_dt
        else:
            slot = current_dt + timedelta(hours=interval_hours)
            slot = adjust_to_safe_posting_window(slot)
            current_dt = slot
        timestamps.append(slot.isoformat())

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
            caption = job.get("caption") or user.get("default_caption_suffix") or "Clonado com Clonify AI #reels"
            share_to_feed = bool(job.get("share_to_feed", user.get("share_to_feed", 0)))

            res = publisher.publish_reel(
                video_url=job["output_path"],
                caption=caption,
                instagram_account_id=ig_account_id,
                access_token=ig_token,
                share_to_feed=share_to_feed
            )
            media_id = res.get("id") if isinstance(res, dict) else None
            if media_id:
                repo.update_job_instagram_media_id(job["id"], media_id)
            repo.mark_job_posted(job["id"])
            processed_count += 1
        except Exception as e:
            logger.error(f"Failed to publish scheduled job {job['id']}: {e}")

    return processed_count


def sync_meta_insights(repo: Any) -> int:
    """
    Polls all posted jobs with an instagram_media_id and fetches updated performance metrics from Meta Graph API.
    """
    conn = repo._connect()
    try:
        cursor = conn.execute("SELECT id, user_id, instagram_media_id FROM jobs WHERE instagram_media_id IS NOT NULL AND status = 'completed'")
        rows = cursor.fetchall()
        posted_jobs = [dict(r) for r in rows]
    finally:
        conn.close()

    if not posted_jobs:
        return 0

    from src.instagram_publisher import InstagramPublisher
    publisher = InstagramPublisher()
    updated_count = 0

    for job in posted_jobs:
        job_id = job["id"]
        media_id = job["instagram_media_id"]
        user_id = job.get("user_id")

        if not media_id:
            continue

        user = repo.get_user_by_id(user_id) if user_id else {}
        token = (user or {}).get("instagram_access_token")

        if not token:
            from src.config import get_settings
            token = get_settings().instagram_access_token

        if not token:
            continue

        try:
            metrics = publisher.fetch_media_insights(media_id, token)
            repo.upsert_media_insights(
                job_id=job_id,
                instagram_media_id=media_id,
                views=metrics.get("views", 0),
                likes=metrics.get("likes", 0),
                comments=metrics.get("comments", 0),
                shares=metrics.get("shares", 0),
                reach=metrics.get("reach", 0),
                engagement_score=metrics.get("engagement_score", 0.0)
            )
            updated_count += 1
        except Exception as e:
            logger.warning(f"Failed to sync insights for job {job_id} / media {media_id}: {e}")

    return updated_count
