# AGENTS.md

Compact agent guide for the **Reels Cloner MVP** — a Python 3.11 CLI + FastAPI webhook that downloads an Instagram Reel, picks the best matching local video via Gemini, and renders a new short with the original audio + a text overlay that avoids faces. Full architecture, data flow, and conventions live in `GEMINI.md` — read that for the pipeline details.

## Trust the code over GEMINI.md
`GEMINI.md` is comprehensive but stale on two points; `src/config.py` and `.env.example` are the source of truth:
- Default Gemini model is `gemini-3.5-flash` (GEMINI.md still says `gemini-2.0-flash`).
- Configured local video folder is `Videos-fuga-novo` (GEMINI.md references `Vídeos do fuga`, which also exists on disk but is not the wired default).

## Commands (run from repo root — the package is `src`)
- Index local videos (must run before clone): `python -m src.main index`
- Clone a Reels: `python -m src.main clone "https://www.instagram.com/reel/<ID>/" [--output-dir DIR]`
- Run API (dev, port 8000): `uvicorn src.app:app --reload`
- API via Docker (bundles FFmpeg + fonts): `docker compose up reels-api`
- Clone via Docker: `docker compose run --rm reels-cloner python -m src.main clone "<URL>"`

## Tests
- Run all: `pytest` (no `pytest.ini`, no `conftest.py`, no `pyproject.toml` — default discovery from repo root).
- Run one file: `pytest tests/test_matcher.py`; one test: `pytest tests/test_matcher.py::test_name`.
- Tests mirror `src/` as `tests/test_<module>.py` — a new module should get a matching test file.
- **No linter, formatter, or typechecker is configured.** "Strict typing" in GEMINI.md is a convention only, not enforced — do not claim `lint`/`typecheck` passes, and do not invent config for one without being asked.

## Setup gotchas
- **FFmpeg + ffprobe must be on PATH** for local runs. The `drawtext` overlay also needs system fonts — Docker installs `fonts-dejavu-core` / `fonts-liberation`; locally ensure equivalent fonts exist or text rendering fails.
- **Instagram downloads require cookies.** yt-dlp auto-loads `data/cookies.txt` (or the `INSTAGRAM_COOKIES_FILE` env var); the Docker path is `/app/data/cookies.txt`. Without cookies most Reels downloads fail.
- **`.env` is loaded by `python-dotenv`** in `src/config.py` and overrides hardcoded defaults. Edit `.env` for runtime config; `.env.example` is only the template.
- **Machine-specific Windows paths are hardcoded as defaults** in `src/config.py` and `docker-compose.yml` (`C:\Users\victor.felix\...\Videos-fuga-novo`). Override with `LOCAL_VIDEOS_DIR` / `DATA_DIR` env vars when running elsewhere.
- **Sensitive defaults live in `src/config.py`**: an Evolution API token, the n8n webhook URL, and a WhatsApp test number. Do not print, log, or expose these further.
- The Gemini SDK is **`google-genai`** (the newer package), not `google-generativeai`. All Gemini calls go through `GeminiClient` in `src/gemini_client.py`.

## Execution order & data layout
- `index` must populate `data/videos.db` before `clone` — `clone_reels_pipeline` raises if no videos are indexed (`src/main.py:45`).
- Pipeline artifacts live under `data/`: `videos.db`, `downloads/`, `frames/`, `audio.aac`, `adjusted.mp4`, `output/`.

## API behavior (`src/app.py`)
- `POST /api/clone` accepts JSON or form-data: `{url, output_dir?, webhook_url?}`. It runs the clone pipeline in a `BackgroundTask` and POSTs the final video as **base64** to the n8n webhook (defaults to `N8N_WEBHOOK_URL`). Returns immediately with `status:"processing"`.
- `GET /health` → `{status, model}`.
