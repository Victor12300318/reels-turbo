# Mobile-First Dashboard & Advanced Instagram Features Specification

## 1. Overview
This specification defines the Mobile-First Web Dashboard enhancement for **Reels Cloner AI**. The platform is optimized for smartphone users with a native app-like experience (Bottom Navigation Bar), 9:16 vertical video player with side-by-side / toggle comparison, custom fixed caption signature (e.g. `Siga @agufzz`), batch scheduling with automatic interval posting (e.g., post every 3h), calendar view for scheduled posts, `share_to_feed` toggle (option to post ONLY on Reels, excluding the main feed), video library management, and analytics metrics.

---

## 2. Key Architecture & Features

### 📱 A. Mobile-First Bottom Navigation (4 Tabs)
1. **⚡ Cloner (Home):** Feed of Reels jobs in vertical 9:16 cards with integrated video player, `Original ↔ IA` comparison toggle, and action buttons (*Post Now*, *Schedule*, *Edit Caption*, *Download MP4*).
2. **📅 Calendar & Batch Schedule:** Visual Calendar showing scheduled posts by date/time, plus a **Batch Scheduler** tool to auto-schedule up to 50 links with configurable posting intervals (e.g. every 1h, 2h, 3h, 6h).
3. **✍️ Editor & Settings:** Editor to adjust extracted text, configure the user's **Default Caption Signature** (e.g. `Siga @agufzz`), and toggle **"Postar Apenas no Reels (Não compartilhar no Feed)"** (`share_to_feed: false`).
4. **📁 Library & Analytics:** Visual grid of indexed local videos with thumbnails, upload zone, delete option, and summary metrics.

### ✍️ B. Fixed Caption Signature (Legenda Fixa)
- Users can set a personal default caption suffix in settings or user profile (e.g., `\n\nSiga @agufzz`).
- When a Reel is cloned, the caption is automatically pre-populated as:
  `{extracted_on_screen_text}\n\n{default_caption_suffix}`

### ⏱️ C. Batch Auto-Interval Scheduler (Agendamento em Lote)
- When multiple URLs are submitted or enqueued, user can select an interval (e.g., `3 horas`).
- The system automatically calculates `scheduled_at` for each video:
  - Video 1: `now()` (or start time)
  - Video 2: `now() + 3 hours`
  - Video 3: `now() + 6 hours`
  - ... and so on up to 50+ videos.
- A background scheduler worker polls every 60 seconds and publishes any job where `status == 'scheduled'` and `scheduled_at <= now()`.

### 🎬 D. 9:16 Video Player & Share to Feed Toggle
- Built-in HTML5 video player styled for vertical mobile screens (aspect-ratio 9:16).
- `share_to_feed` toggle: When posting to Instagram Graph API, passes `share_to_feed: False` so the post appears exclusively in the Reels tab on Instagram, not cluttering the profile grid feed.

---

## 3. Database Schema Updates (`src/database.py`)

### `users` Table Updates:
- `default_caption_suffix`: TEXT (e.g. `Siga @agufzz`)
- `share_to_feed`: INTEGER/BOOLEAN (Default 0 = Reels only, 1 = Share to Feed)
- `default_post_interval_hours`: INTEGER (Default 3)

### `jobs` Table Updates:
- `caption`: TEXT (Customized caption used when publishing)
- `scheduled_at`: TEXT (ISO timestamp if post is scheduled for later)
- `posted_at`: TEXT (ISO timestamp when published to Instagram)
- `share_to_feed`: INTEGER/BOOLEAN (Per-job toggle)

---

## 4. API Endpoints (`src/app.py`)

1. **`POST /api/v1/user/settings`**:
   - Request: `{ "default_caption_suffix": "Siga @agufzz", "share_to_feed": false, "default_post_interval_hours": 3 }`
   - Response: `{ "status": "success", ... }`

2. **`POST /api/v1/jobs/batch-schedule`**:
   - Request: `{ "job_ids": [...], "interval_hours": 3, "start_time": "2026-07-25T15:00:00Z" }`
   - Automatically assigns spaced `scheduled_at` times across all selected jobs.

3. **`GET /api/v1/jobs/calendar`**:
   - Returns all `scheduled` and `completed` jobs grouped or sorted by date for the calendar view.

4. **`POST /api/v1/jobs/{job_id}/publish`**:
   - Request: `{ "caption": "...", "share_to_feed": false }`
   - Triggers `InstagramPublisher().publish_reel(..., share_to_feed=False)` with custom caption immediately.

5. **`DELETE /api/v1/videos/{video_id}`**:
   - Removes video entry from DB and deletes local file from storage.

6. **`GET /api/v1/metrics`**:
   - Returns aggregated statistics: total_cloned, total_published, library_count, scheduled_count.

---

## 5. Verification & Testing
- Unit test for `share_to_feed` parameter in `InstagramPublisher`.
- Unit test for batch interval scheduling calculation.
- Integration test for background scheduler auto-publishing pending scheduled jobs.
