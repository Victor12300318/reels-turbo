# Mobile-First Dashboard & Instagram Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Mobile-First Next.js frontend with bottom navigation tabs, vertical video player, custom fixed caption signature (`Siga @agufzz`), batch interval auto-scheduler, calendar view, and option to post exclusively to Reels (`share_to_feed: false`).

**Architecture:** Extend FastAPI backend and PostgreSQL/SQLite database with user settings and job scheduling metadata. Implement a background worker thread that polls scheduled posts and publishes them to Meta Graph API using `share_to_feed: False`. Redesign Next.js frontend into a mobile-first app with 4 bottom tabs.

**Tech Stack:** Python 3.11+, FastAPI, PostgreSQL / SQLite (`psycopg`), Next.js 14, Tailwind CSS, Lucide Icons, Meta Instagram Graph API, Docker.

## Global Constraints
- Native Mobile-First layout (375px+ responsive viewport with bottom navigation bar).
- No external heavy scheduler dependencies (use background async loop/thread with DB lock).
- Maintain 100% backward compatibility for iOS Shortcuts API headers (`apikey` / `x-api-key`).

---

### Task 1: Database Schema Updates for User Settings & Job Scheduling

**Files:**
- Modify: `src/database.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Produces: `default_caption_suffix`, `share_to_feed`, `default_post_interval_hours` on `users` table; `caption`, `scheduled_at`, `posted_at`, `share_to_feed` on `jobs` table.

- [ ] **Step 1: Write failing test in `tests/test_database.py`**

```python
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
    assert updated_user["share_to_feed"] == 0

    job = repo.create_job(user_id=user["id"], url="https://instagram.com/reel/111/")
    repo.update_job_schedule(
        job_id=job["id"],
        caption="Legenda teste Siga @agufzz",
        scheduled_at="2026-07-25T18:00:00Z",
        share_to_feed=0
    )
    fetched_job = repo.get_job(job["id"])
    assert fetched_job["caption"] == "Legenda teste Siga @agufzz"
    assert fetched_job["scheduled_at"] == "2026-07-25T18:00:00Z"
    assert fetched_job["share_to_feed"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_user_settings_and_job_scheduling -v`
Expected: FAIL (missing methods `update_user_settings` and `update_job_schedule`).

- [ ] **Step 3: Implement database schema migration and methods in `src/database.py`**

```python
# Add columns in ensure_schema() and methods:
def update_user_settings(self, user_id: str, default_caption_suffix: str, share_to_feed: int, default_post_interval_hours: int) -> None:
    conn = self._connect()
    try:
        with conn:
            conn.execute(
                f"UPDATE users SET default_caption_suffix = {self._ph(1)}, share_to_feed = {self._ph(1)}, default_post_interval_hours = {self._ph(1)} WHERE id = {self._ph(1)}",
                (default_caption_suffix, share_to_feed, default_post_interval_hours, user_id)
            )
    finally:
        conn.close()

def update_job_schedule(self, job_id: str, caption: str, scheduled_at: str, share_to_feed: int) -> None:
    conn = self._connect()
    try:
        with conn:
            conn.execute(
                f"UPDATE jobs SET caption = {self._ph(1)}, scheduled_at = {self._ph(1)}, share_to_feed = {self._ph(1)}, status = 'scheduled' WHERE id = {self._ph(1)}",
                (caption, scheduled_at, share_to_feed, job_id)
            )
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::test_user_settings_and_job_scheduling -v`
Expected: PASS

---

### Task 2: Instagram Publisher `share_to_feed` Option

**Files:**
- Modify: `src/instagram_publisher.py`
- Test: `tests/test_instagram_publisher.py`

**Interfaces:**
- Produces: `share_to_feed: bool` parameter in `InstagramPublisher.publish_reel(...)`.

- [ ] **Step 1: Write failing test in `tests/test_instagram_publisher.py`**

```python
@patch("src.instagram_publisher.httpx.post")
@patch("src.instagram_publisher.httpx.get")
def test_publish_reel_share_to_feed_false(mock_get, mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"id": "container_123"}),
        MagicMock(status_code=200, json=lambda: {"id": "media_999"}),
    ]
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})

    publisher = InstagramPublisher()
    result = publisher.publish_reel(
        video_url="https://crm-minio.xjbony.easypanel.host/reels-turbo/sample.mp4",
        caption="Test Reels Only",
        instagram_account_id="17841400000000000",
        access_token="EAAG...",
        share_to_feed=False
    )

    assert result["id"] == "media_999"
    # Verify share_to_feed: False was included in container creation payload
    first_post_data = mock_post.call_args_list[0][1]["data"]
    assert first_post_data.get("share_to_feed") == "false"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_instagram_publisher.py::test_publish_reel_share_to_feed_false -v`
Expected: FAIL

- [ ] **Step 3: Update `src/instagram_publisher.py` to support `share_to_feed`**

```python
    def _create_container(self, account_id: str, access_token: str, video_url: str, caption: str, share_to_feed: bool = True) -> tuple[str, str]:
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": access_token,
            "share_to_feed": "true" if share_to_feed else "false",
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_instagram_publisher.py::test_publish_reel_share_to_feed_false -v`
Expected: PASS

---

### Task 3: Batch Scheduler API & Background Auto-Publisher Loop

**Files:**
- Create: `src/scheduler.py`
- Modify: `src/app.py`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Produces: `POST /api/v1/user/settings`, `POST /api/v1/jobs/batch-schedule`, `GET /api/v1/jobs/calendar`, background polling loop checking for due scheduled posts.

- [ ] **Step 1: Write failing test in `tests/test_scheduler.py`**

```python
from src.scheduler import calculate_batch_timestamps

def test_calculate_batch_timestamps():
    timestamps = calculate_batch_timestamps(
        count=3,
        start_time_iso="2026-07-25T12:00:00Z",
        interval_hours=3
    )
    assert len(timestamps) == 3
    assert timestamps[0] == "2026-07-25T12:00:00Z"
    assert timestamps[1] == "2026-07-25T15:00:00Z"
    assert timestamps[2] == "2026-07-25T18:00:00Z"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `src/scheduler.py` and endpoints in `src/app.py`**

```python
from datetime import datetime, timedelta, timezone

def calculate_batch_timestamps(count: int, start_time_iso: str, interval_hours: int) -> list[str]:
    start_dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
    result = []
    for i in range(count):
        t = start_dt + timedelta(hours=i * interval_hours)
        result.append(t.isoformat())
    return result
```

In `src/app.py`:
- Add `POST /api/v1/user/settings`
- Add `POST /api/v1/jobs/batch-schedule`
- Add `GET /api/v1/jobs/calendar`
- Add background scheduler task that runs every 60s and publishes jobs where `scheduled_at <= now()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS

---

### Task 4: Mobile-First Frontend Next.js (4 Tabs, Vertical Player, Calendar, Settings)

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Produces: Responsive Mobile-First Bottom Navigation Bar (Clonador, Calendário, Editor/Config, Biblioteca), 9:16 vertical player with comparison toggle, fixed caption input, batch interval scheduler modal, and calendar view.

- [ ] **Step 1: Update `frontend/app/page.tsx` with 4 bottom tabs and mobile-first responsive layout**

In `frontend/app/page.tsx`:
- Render Fixed Bottom Bar with 4 icons:
  1. ⚡ **Clonador** (Player 9:16 + Original/IA toggle + Post Now/Schedule)
  2. 📅 **Calendário** (Visual schedule list & Batch Interval auto-scheduler)
  3. ✍️ **Editor & Configs** (Legenda Fixa, share_to_feed toggle, Meta OAuth, iOS Key)
  4. 📁 **Biblioteca** (Local video grid with delete action + upload)

- [ ] **Step 2: Build Next.js app to ensure zero TypeScript/lint errors**

Run: `docker compose up -d --build`
Expected: Successfully built and running containers.

- [ ] **Step 3: Verify all tests pass**

Run: `pytest`
Expected: ALL 39+ tests pass.
