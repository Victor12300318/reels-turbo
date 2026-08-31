# AGENTS.md

Clonify AI is a Python 3.11+ backend (CLI + FastAPI) with a Next.js frontend. Run backend commands from the repository root; run npm commands from `frontend/`.

## Source Of Truth

- `src/config.py` and `.env.example` define runtime configuration. `GEMINI.md` is useful legacy context but still contains stale model and local-video values.
- `.env` is loaded by `python-dotenv`; never print, commit, or expose its credentials. `data/`, cookies, and uploaded media are ignored by git.
- The code default is `gemini-3.5-flash` and `DATA_DIR=./data`. Without `LOCAL_VIDEOS_DIR`, the code falls back to the machine-specific `C:\Users\victor.felix\Pictures\reels-turbo\Videos-fuga-novo`; `.env.example` explicitly sets `./data/videos`, so set the variable for a new machine.
- Set `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `JWT_SECRET` explicitly for a deployment; the API contains development fallbacks.

## Commands

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
pytest tests/test_app.py::test_health_check -q
python -m src.main index
python -m src.main clone "https://www.instagram.com/reel/<ID>/" [--output-dir DIR]
uvicorn src.app:app --reload
```

- The local API listens on port 8000. `index` must populate the video repository before CLI/API cloning; cloning raises when no candidate videos are indexed.
- Frontend commands from `frontend/`: `npm install`, `npm run dev` (port 3000), `npm run build`, and `npm run start`; in PowerShell use the equivalent `npm.cmd` form if execution policy blocks `npm.ps1`.
- Docker commands: `docker compose build`; `docker compose up` (API host port 8008, frontend host port 3008); `docker compose up reels-api` for the API only.
- Compose defines only `reels-api` and `reels-frontend`; there is no `reels-cloner` service. Compose also overrides the backend image's default indexing command with Uvicorn.
- There is no pytest config, CI workflow, pre-commit config, Python linter/formatter/typechecker, or frontend lint script. Use `pytest` and `npm run build` rather than inventing checks.

## Architecture

- `src/main.py` owns the CLI and clone pipeline: download with yt-dlp, analyze/match with an AI client, then render with FFmpeg.
- `src/app.py` owns FastAPI auth, jobs, uploads, scheduling, OAuth, Meta webhooks, and the dashboard API. `/api/v1/clone` and `/api/clone` create a job and return `status: "processing"`.
- API clone jobs go through the in-process FIFO worker in `src/app.py`; FastAPI startup also polls due scheduled jobs every 60 seconds.
- `src/database.py` owns `VideoRepository` and schema creation. It uses PostgreSQL when `DATABASE_URL` is a Postgres URL, otherwise SQLite at `<DATA_DIR>/videos.db`; `ensure_schema()` is the migration mechanism. The API falls back to SQLite if configured PostgreSQL cannot connect.
- `src/ai_client.py` selects Gemini or OpenRouter from `system_settings`; keep analyzer/matcher provider calls behind that client interface. The Gemini SDK is `google-genai`, not `google-generativeai`.
- `src/video_processor.py` and `src/ffmpeg_utils.py` own media processing. Current rendering crops/re-encodes to 1080x1920 and places overlay text in a face-safe zone.
- `src/text_style.py` defines user overlay preferences and the bundled social font catalog in `assets/fonts`; frontend previews use copies in `frontend/public/fonts`.
- `src/database.py` tracks per-user rotation cycles in `video_cycle_usage` and exactly-once publishing through `jobs.publish_state`.
- `src/scheduler.py` and `src/instagram_publisher.py` own automatic posting and insights. Scheduling is constrained to 06:00-21:00 in UTC-3.
- `frontend/app/` is the Next dashboard. Browser requests use `/api/v1`; `frontend/next.config.js` rewrites them to `INTERNAL_API_URL` (the Compose service is `http://reels-api:8000`).

## Runtime Gotchas

- Local media processing needs both `ffmpeg` and `ffprobe` on `PATH`, plus a drawtext-compatible system font. The backend Docker image installs FFmpeg and Liberation/DejaVu fonts.
- Instagram downloads use yt-dlp cookies from `INSTAGRAM_COOKIES_FILE` or an existing `data/cookies.txt`/`/app/data/cookies.txt`. Without cookies, downloads commonly fail; keep the file private.
- Compose forces `LOCAL_VIDEOS_DIR=/app/videos` but mounts only `./data`; mount the host video library into `/app/videos` before indexing or cloning in Docker.
- S3 uploads are best-effort, but automatic Meta publishing requires the rendered video to have a public `http(s)` URL. A local fallback path will not satisfy that requirement.
- Pipeline artifacts are under `DATA_DIR`: `videos.db`, `downloads/`, `frames/`, `audio.aac`, `adjusted.mp4`, `output/`, and per-user uploads.

## Tests

- Tests live in `tests/test_<module>.py`; use `tmp_path` for disposable repository/database state and mock Gemini, Meta, S3, yt-dlp, and FFmpeg calls rather than making network requests.
- Add a matching test file for new backend modules. App tests use FastAPI `TestClient` and initialize the configured repository, so avoid relying on a live external service.
