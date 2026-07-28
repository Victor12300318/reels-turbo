# Implementation Plan: Library Previews, Anti-Repetition, Safe Posting Window & RAG Meta Insights

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve Clonify AI with video thumbnails/streaming previews, an anti-repetition weighted rotation algorithm, a 06:00-21:00 safe posting window, and a RAG performance feedback loop using Gemini `text-embedding-004` and Meta Graph API Insights.

**Architecture:** 
- **Database (`src/database.py`):** Schema migration for `videos` (`usage_count`, `last_used_at`), `jobs` (`instagram_media_id`, `embedding`), and new `media_insights` table.
- **Matcher & Anti-Repetition (`src/matcher.py`):** Weighted candidate ranking based on visual affinity score adjusted by usage frequency and recency decay.
- **Safe Posting Window (`src/scheduler.py`):** Datetime adjustment function enforcing 06:00-21:00 (UTC-3) posting hours.
- **RAG & Insights (`src/ai_client.py`, `src/instagram_publisher.py`, `src/app.py`):** Meta Graph API `/insights` collection, Gemini `text-embedding-004` vector generation, and Top 5 performance prompt injection.
- **Frontend (`frontend/app/page.tsx`):** Video thumbnails, interactive video preview player modal in Library and Cloner feed, and manual Meta sync trigger.

**Tech Stack:** Python 3.11+, FastAPI, SQLite / PostgreSQL (`psycopg`), `google-genai` SDK (`text-embedding-004`), Next.js, Tailwind CSS, Lucide React icons.

## Global Constraints
- Database compatibility with both SQLite and PostgreSQL.
- Modern Clean Light SaaS design system (ManyChat style, zero emojis).
- Full test coverage via `pytest` with zero test regressions.

---

### Task 1: Database Schema & Usage Counter Repository Operations

**Files:**
- Modify: `src/database.py:70-200, 360-400`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: `VideoRepository._connect()`, `VideoRepository._ph()`
- Produces: `increment_video_usage(video_id: str)`, `upsert_media_insights(job_id, media_id, metrics)`, `get_top_performing_reels(user_id, top_k=5)`

- [ ] **Step 1: Write failing tests for usage tracking and insights DB methods**

```python
def test_video_usage_increment_and_insights(repo):
    # Test video usage increment
    video = repo.upsert({
        "path": "C:\\videos\\v1.mp4",
        "filename": "v1.mp4",
        "description": "Video 1",
        "themes": "test",
        "orientation": "portrait",
        "duration_seconds": 10.0,
        "has_face": 0,
        "frame_paths": ["f1.jpg"],
    })
    repo.increment_video_usage(video["id"])
    v_updated = repo.get_video_by_id(video["id"])
    assert v_updated["usage_count"] == 1
    assert v_updated["last_used_at"] is not None

    # Test media_insights upsert and query
    repo.upsert_media_insights(
        job_id="job_123",
        instagram_media_id="media_999",
        views=15000,
        likes=800,
        comments=45,
        shares=120,
        reach=18000,
        engagement_score=19500.0
    )
    top_reels = repo.get_top_performing_reels(user_id=None, top_k=5)
    assert len(top_reels) >= 1
    assert top_reels[0]["views"] == 15000
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_database.py::test_video_usage_increment_and_insights -v`  
Expected: FAIL (missing methods / columns)

- [ ] **Step 3: Update `src/database.py` schema and repository methods**

Add `usage_count INTEGER DEFAULT 0`, `last_used_at TEXT` to `videos`, `instagram_media_id TEXT UNIQUE`, `embedding TEXT` to `jobs`, create `media_insights` table, and implement `increment_video_usage`, `upsert_media_insights`, `get_top_performing_reels`, and `get_video_by_id`.

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_database.py`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat(database): add video usage tracking, media_insights table, and top performing reels repository queries"
```

---

### Task 2: Anti-Repetition Weighted Rotation in Matcher

**Files:**
- Modify: `src/matcher.py:10-70`
- Test: `tests/test_matcher.py`

**Interfaces:**
- Consumes: `candidates: list[dict[str, Any]]` with `usage_count` and `last_used_at`
- Produces: `Matcher.rank_candidates` with usage decay and bonus penalty scoring

- [ ] **Step 1: Write failing test for weighted candidate ranking**

```python
def test_matcher_weighted_usage_penalty(monkeypatch):
    from src.matcher import Matcher
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    # Mock LLM returning candidate 1 as top visual match
    mock_client.analyze.return_value = '{"ranking": [{"video_id": 1, "reason": "Good match"}, {"video_id": 2, "reason": "Ok match"}]}'

    matcher = Matcher(mock_client)
    candidates = [
        {"id": 1, "description": "Vid 1", "usage_count": 5, "last_used_at": "2026-07-25T10:00:00Z"},
        {"id": 2, "description": "Vid 2", "usage_count": 0, "last_used_at": None},
    ]

    ranked = matcher.rank_candidates("reference description", candidates, top_k=2)
    # Candidate 2 (never used) should be boosted over candidate 1 (used 5 times)
    assert ranked[0]["id"] == 2
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_matcher.py::test_matcher_weighted_usage_penalty -v`  
Expected: FAIL

- [ ] **Step 3: Implement usage penalty and bonus calculation in `Matcher.rank_candidates`**

Calculate adjusted score = base_llm_score + bonus(usage_count == 0: +20) - penalty_recency(30 * (7 - days_since_use)/7) - penalty_frequency(usage_count * 5). Sort candidates by adjusted score.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_matcher.py`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/matcher.py tests/test_matcher.py
git commit -m "feat(matcher): implement anti-repetition weighted rotation algorithm"
```

---

### Task 3: Safe Posting Window Algorithm (06:00 to 21:00 UTC-3)

**Files:**
- Modify: `src/scheduler.py:1-30`, `src/app.py:270-300, 675-695`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: ISO timestamp / datetime object
- Produces: `adjust_to_safe_posting_window(dt: datetime, timezone_offset_hours: int = -3) -> datetime`

- [ ] **Step 1: Write failing test for safe posting window adjustment**

```python
from datetime import datetime, timezone
from src.scheduler import adjust_to_safe_posting_window

def test_safe_posting_window_adjustment():
    # 02:00 AM UTC-3 (05:00 UTC) -> should bump to 06:00 AM UTC-3 (09:00 UTC)
    late_night_utc = datetime(2026, 7, 25, 5, 0, tzinfo=timezone.utc)
    safe_dt = adjust_to_safe_posting_window(late_night_utc, timezone_offset_hours=-3)
    
    # Hour in UTC-3 should be 6:00 AM
    local_hour = (safe_dt.hour - 3) % 24
    assert local_hour == 6

    # 14:00 PM UTC-3 -> stays within window (14:00)
    daytime_utc = datetime(2026, 7, 25, 17, 0, tzinfo=timezone.utc)
    safe_dt_day = adjust_to_safe_posting_window(daytime_utc, timezone_offset_hours=-3)
    assert safe_dt_day == daytime_utc
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_scheduler.py::test_safe_posting_window_adjustment -v`  
Expected: FAIL

- [ ] **Step 3: Implement `adjust_to_safe_posting_window` and update batch timestamp calculations**

Add `adjust_to_safe_posting_window` in `src/scheduler.py`. Update `calculate_batch_timestamps` and dynamic queue scheduling in `src/app.py` to ensure all scheduled slots fall strictly between 06:00 AM and 21:00 PM (UTC-3).

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_scheduler.py`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/scheduler.py src/app.py tests/test_scheduler.py
git commit -m "feat(scheduler): implement 06:00 to 21:00 safe posting window adjustment"
```

---

### Task 4: Gemini Embedding & RAG Context Engine

**Files:**
- Modify: `src/ai_client.py`, `src/matcher.py`, `src/analyzer.py`
- Test: `tests/test_ai_client.py`

**Interfaces:**
- Consumes: `GeminiClient`, `OpenRouterClient`, `VideoRepository`
- Produces: `client.get_embedding(text: str) -> list[float]`, `get_top_performing_reels_context(repo, user_id)`

- [ ] **Step 1: Write failing test for Gemini embedding generation**

```python
def test_gemini_client_get_embedding(monkeypatch):
    from src.gemini_client import GeminiClient
    from unittest.mock import MagicMock

    client = GeminiClient(api_key="fake_key")
    mock_embed = MagicMock()
    mock_embed.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    client.client.models.embed_content = MagicMock(return_value=mock_embed)

    vector = client.get_embedding("Texto de teste")
    assert isinstance(vector, list)
    assert len(vector) == 3
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_ai_client.py::test_gemini_client_get_embedding -v`  
Expected: FAIL

- [ ] **Step 3: Implement `get_embedding` in AI clients and add RAG context builder in `src/matcher.py`**

In `GeminiClient`, call `self.client.models.embed_content(model="text-embedding-004", contents=text)`. In `OpenRouterClient`, implement fallback embedding vector. Inject top performing reels context into `Matcher.rank_candidates` and `Analyzer.analyze_text_style`.

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_ai_client.py`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/ai_client.py src/matcher.py src/analyzer.py tests/test_ai_client.py
git commit -m "feat(rag): implement Gemini text-embedding-004 and top performing reels prompt context injection"
```

---

### Task 5: Meta Graph API Insights Collector & Sync Endpoints

**Files:**
- Modify: `src/instagram_publisher.py`, `src/scheduler.py`, `src/app.py`
- Test: `tests/test_instagram_publisher.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: Meta Graph API `/v19.0/{media_id}/insights`
- Produces: `InstagramPublisher.fetch_media_insights()`, `sync_meta_insights(repo)`, `POST /api/v1/insights/sync`

- [ ] **Step 1: Write failing test for Meta insights fetching and sync**

```python
def test_fetch_media_insights(monkeypatch):
    from src.instagram_publisher import InstagramPublisher
    from unittest.mock import MagicMock

    pub = InstagramPublisher()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"name": "plays", "values": [{"value": 12000}]},
            {"name": "likes", "values": [{"value": 500}]},
            {"name": "comments", "values": [{"value": 30}]},
            {"name": "shares", "values": [{"value": 80}]},
            {"name": "reach", "values": [{"value": 15000}]},
        ]
    }
    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: mock_response)

    metrics = pub.fetch_media_insights("media_123", "access_token")
    assert metrics["views"] == 12000
    assert metrics["likes"] == 500
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_instagram_publisher.py::test_fetch_media_insights -v`  
Expected: FAIL

- [ ] **Step 3: Implement `fetch_media_insights`, `sync_meta_insights`, and `POST /api/v1/insights/sync` endpoint**

Add `fetch_media_insights` in `InstagramPublisher`. Add `sync_meta_insights` in `src/scheduler.py` (and trigger in background scheduler). Add `POST /api/v1/insights/sync` endpoint in `src/app.py`. Save `instagram_media_id` when publishing reels.

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_instagram_publisher.py tests/test_app.py`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/instagram_publisher.py src/scheduler.py src/app.py tests/test_instagram_publisher.py tests/test_app.py
git commit -m "feat(insights): implement Meta Graph API insights collection daemon and manual sync endpoint"
```

---

### Task 6: Video Thumbnail & Streaming API Endpoints

**Files:**
- Modify: `src/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: Video ID, video path, frame_paths
- Produces: `GET /api/v1/videos/{video_id}/thumbnail`, `GET /api/v1/videos/{video_id}/stream`

- [ ] **Step 1: Write failing test for video thumbnail and streaming endpoints**

```python
def test_video_thumbnail_and_stream_endpoints(tmp_path):
    from src.app import app, get_repo
    from fastapi.testclient import TestClient
    client = TestClient(app)

    repo = get_repo()
    frame_file = tmp_path / "frame.jpg"
    frame_file.write_bytes(b"fake_jpg_data")
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake_mp4_data")

    vid = repo.upsert({
        "path": str(video_file),
        "filename": "test.mp4",
        "description": "Test",
        "themes": "test",
        "orientation": "portrait",
        "duration_seconds": 5.0,
        "has_face": 0,
        "frame_paths": [str(frame_file)],
    })

    res_thumb = client.get(f"/api/v1/videos/{vid['id']}/thumbnail")
    assert res_thumb.status_code == 200

    res_stream = client.get(f"/api/v1/videos/{vid['id']}/stream")
    assert res_stream.status_code == 200
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_app.py::test_video_thumbnail_and_stream_endpoints -v`  
Expected: FAIL

- [ ] **Step 3: Implement `thumbnail` and `stream` endpoints in `src/app.py`**

Add `GET /api/v1/videos/{video_id}/thumbnail` returning FileResponse for the first frame and `GET /api/v1/videos/{video_id}/stream` supporting media streaming with range requests.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_app.py`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/app.py tests/test_app.py
git commit -m "feat(api): add video thumbnail and media streaming endpoints"
```

---

### Task 7: Frontend UI - Video Previews & Player Modal (Library & Cloner Tabs)

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `/api/v1/videos/{id}/thumbnail`, `/api/v1/videos/{id}/stream`, `/api/v1/insights/sync`
- Produces: Updated Library grid with thumbnails, usage badges, video player modal popup, and Meta Sync button.

- [ ] **Step 1: Add Video Player Modal state and preview thumbnail cards to Library and Cloner Feed**

In `frontend/app/page.tsx`:
- Render video thumbnail image in each library card using `/api/v1/videos/{vid.id}/thumbnail`.
- Add badges showing `Usado X vezes` and last used date.
- Add Video Modal popup trigger to open `<video src="/api/v1/videos/{id}/stream" controls autoPlay />` when clicking any library card thumbnail or reference/matched video thumbnail in the Cloner feed.
- Add "Sincronizar Métricas Meta" button with spinning loader in Settings / Admin tab.

- [ ] **Step 2: Verify frontend TypeScript build**

Run: `cd frontend && npm run build`  
Expected: Successful build with zero errors.

- [ ] **Step 3: Commit changes**

```bash
git add frontend/app/page.tsx
git commit -m "feat(ui): add video thumbnails, interactive video player modal, and Meta Insights sync button"
```
