# Reels Cloner MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python 3.11+ CLI that downloads an Instagram Reels, selects the best local video from an indexed folder, and produces a new clip with the reference audio and on-screen text overlaid opposite to the speaker's face.

**Architecture:** Modular pipeline split into configuration, database (SQLite), FFmpeg helpers, Gemini client, analysis/indexing, matching, video processing, and a CLI entry point. Each module has a single responsibility and communicates through narrow interfaces. Tests use mocking for external APIs and command assertions for FFmpeg to keep the feedback loop fast.

**Tech Stack:** Python 3.11, `yt-dlp`, `google-genai`, `ffmpeg-python` (optional) or direct `subprocess` calls to `ffmpeg`/`ffprobe`, `Pillow`, `pytest`, SQLite3 (stdlib), Docker/Docker Compose.

## Global Constraints

- Python 3.11+
- All source code lives under `src/`; tests under `tests/` mirroring `src/` structure.
- All media I/O uses temporary/working directories under `data/`.
- `GEMINI_API_KEY` must be set; default model is `gemini-2.0-flash`.
- Local video folder default: `C:\Users\victor.felix\Pictures\reels-turbo\Vídeos do fuga`.
- FFmpeg must be available in `PATH` (or inside the Docker image).
- No placeholders (TBD/TODO/etc.) in code or plans.

---

## File Structure

```text
reels-turbo/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI: index / clone
│   ├── config.py            # Settings dataclass + env loading
│   ├── database.py          # SQLite repository for local video metadata
│   ├── gemini_client.py     # Thin wrapper around google-genai
│   ├── ffmpeg_utils.py      # FFmpeg/FFprobe subprocess helpers
│   ├── analyzer.py          # Gemini-driven description / OCR / face-position
│   ├── indexer.py           # Index local videos into the database
│   ├── downloader.py        # Reels download via yt-dlp
│   ├── matcher.py           # Rank + multimodal selection of best local video
│   └── video_processor.py   # Audio extraction, loop/trim, text overlay render
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_gemini_client.py
│   ├── test_ffmpeg_utils.py
│   ├── test_analyzer.py
│   ├── test_indexer.py
│   ├── test_downloader.py
│   ├── test_matcher.py
│   ├── test_video_processor.py
│   └── test_main.py
├── data/
│   ├── downloads/
│   ├── frames/
│   ├── output/
│   └── videos.db
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

### Task 1: Project Bootstrap

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create directories: `data/downloads`, `data/frames`, `data/output`, `tests`

**Interfaces:**
- Consumes: none
- Produces: `Settings` dataclass with fields `gemini_api_key`, `gemini_model`, `local_videos_dir`, `data_dir`, `frames_per_video`, `log_level`. Exposed as `src.config.get_settings()`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
import os
import pytest
from src.config import Settings, get_settings


def test_settings_from_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("LOCAL_VIDEOS_DIR", "C:\\local_videos")
    monkeypatch.setenv("DATA_DIR", "C:\\data")

    settings = get_settings()
    assert settings.gemini_api_key == "test-key"
    assert settings.gemini_model == "gemini-test"
    assert settings.local_videos_dir == "C:\\local_videos"
    assert settings.data_dir == "C:\\data"
```

Run:

```bash
python -m pytest tests/test_config.py -v
```

Expected: FAIL (`ModuleNotFoundError: No module named 'src.config'` or `ImportError`).

- [ ] **Step 2: Create `__init__.py` files**

Create empty files:

```bash
New-Item -ItemType File -Path "src/__init__.py" -Force | Out-Null
New-Item -ItemType File -Path "tests/__init__.py" -Force | Out-Null
```

- [ ] **Step 3: Implement `requirements.txt`**

```text
google-genai>=1.0.0
yt-dlp>=2025.0.0
Pillow>=10.0.0
pytest>=8.0.0
python-dotenv>=1.0.0
```

- [ ] **Step 3: Implement `.env.example`**

```bash
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
LOCAL_VIDEOS_DIR=C:\Users\victor.felix\Pictures\reels-turbo\Vídeos do fuga
DATA_DIR=./data
FRAMES_PER_VIDEO=3
LOG_LEVEL=INFO
```

- [ ] **Step 4: Implement `src/config.py`**

```python
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"
    local_videos_dir: str = r"C:\Users\victor.felix\Pictures\reels-turbo\Vídeos do fuga"
    data_dir: str = "./data"
    frames_per_video: int = 3
    log_level: str = "INFO"


def get_settings() -> Settings:
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        local_videos_dir=os.getenv("LOCAL_VIDEOS_DIR", r"C:\Users\victor.felix\Pictures\reels-turbo\Vídeos do fuga"),
        data_dir=os.getenv("DATA_DIR", "./data"),
        frames_per_video=int(os.getenv("FRAMES_PER_VIDEO", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "chore: bootstrap project with config and deps"
```

---

### Task 2: Gemini Client

**Files:**
- Create: `src/gemini_client.py`
- Create: `tests/test_gemini_client.py`

**Interfaces:**
- Consumes: `Settings` from Task 1
- Produces: `GeminiClient.analyze(images: list[Image.Image], prompt: str, response_schema: dict | None = None) -> str | dict`. `images` may be empty (text-only prompt supported).

- [ ] **Step 1: Write the failing test**

Create `tests/test_gemini_client.py`:

```python
from unittest.mock import MagicMock, patch
from PIL import Image
from src.gemini_client import GeminiClient


@patch("src.gemini_client.Client")
def test_analyze_text_only(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Mock response")
    mock_client_class.return_value = mock_client

    client = GeminiClient(api_key="test-key", model="gemini-test")
    result = client.analyze([], "Describe this")

    assert result == "Mock response"
    mock_client.models.generate_content.assert_called_once()


@patch("src.gemini_client.Client")
def test_analyze_with_image(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Image response")
    mock_client_class.return_value = mock_client

    client = GeminiClient(api_key="test-key", model="gemini-test")
    img = Image.new("RGB", (10, 10), color="red")
    result = client.analyze([img], "What do you see?")

    assert result == "Image response"
```

Run:

```bash
python -m pytest tests/test_gemini_client.py -v
```

Expected: FAIL (`ModuleNotFoundError` for `src.gemini_client`).

- [ ] **Step 2: Implement `src/gemini_client.py`**

```python
from typing import Any
from PIL import Image
from google.genai import Client
from google.genai.types import Content, Part


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.client = Client(api_key=api_key)
        self.model = model

    def analyze(
        self,
        images: list[Image.Image],
        prompt: str,
        response_schema: dict | None = None,
    ) -> str | dict[str, Any]:
        parts: list[Part] = [Part.from_text(prompt)]
        for image in images:
            parts.append(Part.from_image(image))

        config = {"temperature": 0.3, "max_output_tokens": 2048}
        if response_schema:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_schema

        response = self.client.models.generate_content(
            model=self.model,
            contents=[Content(role="user", parts=parts)],
            config=config,
        )
        return response.text
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_gemini_client.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/gemini_client.py tests/test_gemini_client.py
git commit -m "feat: add gemini client wrapper"
```

---

### Task 3: SQLite Repository

**Files:**
- Create: `src/database.py`
- Create: `tests/test_database.py`

**Interfaces:**
- Consumes: `Settings`
- Produces: `VideoRepository` with `ensure_schema()`, `upsert(video: dict)`, `get_all()`, `get_by_path(path: str)`, `mark_indexed(path)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_database.py`:

```python
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
        "frame_paths": '["frame1.jpg", "frame2.jpg"]',
    })
    rows = repo.get_all()
    assert len(rows) == 1
    assert rows[0]["filename"] == "sample.mp4"
    assert rows[0]["description"] == "A sample video"


def test_get_by_path(repo):
    repo.upsert({
        "path": "C:\\videos\\sample.mp4",
        "filename": "sample.mp4",
        "description": "A sample video",
        "themes": "",
        "orientation": "",
        "duration_seconds": 0.0,
        "has_face": 0,
        "frame_paths": "[]",
    })
    row = repo.get_by_path("C:\\videos\\sample.mp4")
    assert row is not None
    assert row["filename"] == "sample.mp4"
```

Run:

```bash
python -m pytest tests/test_database.py -v
```

Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 2: Implement `src/database.py`**

```python
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_row(row: sqlite3.Row) -> dict[str, Any]:
    mapped = dict(row)
    try:
        mapped["frame_paths"] = json.loads(mapped.get("frame_paths", "[]") or "[]")
    except json.JSONDecodeError:
        mapped["frame_paths"] = []
    return mapped


class VideoRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    description TEXT,
                    themes TEXT,
                    orientation TEXT,
                    duration_seconds REAL,
                    has_face INTEGER,
                    frame_paths TEXT,
                    updated_at TEXT
                )
            """)

    def upsert(self, video: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO videos (
                    path, filename, description, themes, orientation,
                    duration_seconds, has_face, frame_paths, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    filename=excluded.filename,
                    description=excluded.description,
                    themes=excluded.themes,
                    orientation=excluded.orientation,
                    duration_seconds=excluded.duration_seconds,
                    has_face=excluded.has_face,
                    frame_paths=excluded.frame_paths,
                    updated_at=excluded.updated_at
            """, (
                video["path"],
                video["filename"],
                video.get("description", ""),
                video.get("themes", ""),
                video.get("orientation", ""),
                video.get("duration_seconds", 0.0),
                int(video.get("has_face", 0)),
                json.dumps(video.get("frame_paths", [])) if isinstance(video.get("frame_paths"), list) else video.get("frame_paths", "[]"),
                datetime.now(timezone.utc).isoformat(),
            ))

    def get_all(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM videos").fetchall()
        return [_parse_row(r) for r in rows]

    def get_by_path(self, path: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM videos WHERE path = ?", (path,)).fetchone()
        return _parse_row(row) if row else None

    def mark_indexed(self, path: str) -> None:
        # Not needed for MVP; kept as hook for future metadata flags
        pass
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_database.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: add sqlite repository for video metadata"
```

---

### Task 4: FFmpeg Helpers

**Files:**
- Create: `src/ffmpeg_utils.py`
- Create: `tests/test_ffmpeg_utils.py`

**Interfaces:**
- Consumes: none
- Produces: `get_duration(path: str) -> float`, `extract_frames(video_path: str, timestamps: list[float], output_dir: str) -> list[str]`, `run_ffmpeg(args: list[str]) -> None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ffmpeg_utils.py`:

```python
from unittest.mock import patch, MagicMock
from src import ffmpeg_utils


def test_get_duration_parses_json():
    sample_json = '{"format": {"duration": "15.230000"}}'
    with patch("src.ffmpeg_utils.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=sample_json, returncode=0)
        duration = ffmpeg_utils.get_duration("video.mp4")
    assert duration == 15.23


def test_extract_frames_builds_correct_commands():
    with patch("src.ffmpeg_utils.subprocess.run") as mock_run, \
         patch("src.ffmpeg_utils.Path.mkdir"):
        mock_run.return_value = MagicMock(returncode=0)
        paths = ffmpeg_utils.extract_frames("video.mp4", [0.0, 2.5], "frames/")
    assert len(paths) == 2
    assert paths[0].endswith("frame_0000.jpg")
    assert paths[1].endswith("frame_0250.jpg")
```

Run:

```bash
python -m pytest tests/test_ffmpeg_utils.py -v
```

Expected: FAIL.

- [ ] **Step 2: Implement `src/ffmpeg_utils.py`**

```python
import json
import shutil
import subprocess
from pathlib import Path


def _ffprobe_path() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def _ffmpeg_path() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def get_duration(video_path: str) -> float:
    result = subprocess.run(
        [
            _ffprobe_path(),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def extract_frames(video_path: str, timestamps: list[float], output_dir: str) -> list[str]:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    base = Path(video_path).stem
    for ts in timestamps:
        ms = int(ts * 1000)
        filename = out_path / f"{base}_frame_{ms:06d}.jpg"
        subprocess.run(
            [
                _ffmpeg_path(),
                "-y",
                "-ss", str(ts),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                str(filename),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        generated.append(str(filename))
    return generated


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run([_ffmpeg_path(), *args], check=True)


def calculate_frame_timestamps(duration: float, n: int) -> list[float]:
    if n <= 1:
        return [0.0]
    step = duration / (n + 1)
    return [step * i for i in range(1, n + 1)]
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_ffmpeg_utils.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/ffmpeg_utils.py tests/test_ffmpeg_utils.py
git commit -m "feat: add ffmpeg helpers for duration and frame extraction"
```

---

### Task 5: Video Analyzer

**Files:**
- Create: `src/analyzer.py`
- Create: `tests/test_analyzer.py`

**Interfaces:**
- Consumes: `GeminiClient` from Task 2, `ffmpeg_utils` from Task 4
- Produces: `VideoAnalyzer.describe(frames) -> dict[str, Any]`, `VideoAnalyzer.extract_text(frames) -> str`, `VideoAnalyzer.detect_face_position(frame) -> str` (one of `top`, `center`, `bottom`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_analyzer.py`:

```python
from unittest.mock import MagicMock
from PIL import Image
from src.analyzer import VideoAnalyzer


def test_detect_face_position():
    mock_client = MagicMock()
    mock_client.analyze.return_value = "top"
    analyzer = VideoAnalyzer(mock_client)
    img = Image.new("RGB", (10, 10), color="blue")
    result = analyzer.detect_face_position(img)
    assert result == "top"


def test_extract_text():
    mock_client = MagicMock()
    mock_client.analyze.return_value = "hello world"
    analyzer = VideoAnalyzer(mock_client)
    img = Image.new("RGB", (10, 10))
    text = analyzer.extract_text([img, img])
    assert text == "hello world"


def test_describe_video():
    mock_client = MagicMock()
    mock_client.analyze.return_value = '{"description": "Beach scene", "themes": "beach,summer", "orientation": "portrait", "has_face": 0}'
    analyzer = VideoAnalyzer(mock_client)
    img = Image.new("RGB", (10, 10))
    result = analyzer.describe([img, img])
    assert result["description"] == "Beach scene"
    assert result["themes"] == "beach,summer"
```

Run:

```bash
python -m pytest tests/test_analyzer.py -v
```

Expected: FAIL.

- [ ] **Step 2: Implement `src/analyzer.py`**

```python
import json
from typing import Any
from PIL import Image
from src.gemini_client import GeminiClient


class VideoAnalyzer:
    def __init__(self, client: GeminiClient):
        self.client = client

    def describe(self, frames: list[Image.Image]) -> dict[str, Any]:
        prompt = """
You are analyzing frames from a short-form video. Provide a structured summary:
- description: a concise paragraph of the scene, content and style
- themes: comma-separated keywords (max 5)
- orientation: "portrait", "landscape", or "square"
- has_face: 1 if a human face is clearly visible, 0 otherwise

Return valid JSON only. Do not wrap in markdown.
"""
        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "themes": {"type": "string"},
                "orientation": {"type": "string"},
                "has_face": {"type": "integer"},
            },
            "required": ["description", "themes", "orientation", "has_face"],
        }
        raw = self.client.analyze(frames, prompt, response_schema=schema)
        data = json.loads(raw) if isinstance(raw, str) else raw
        return {
            "description": data.get("description", ""),
            "themes": data.get("themes", ""),
            "orientation": data.get("orientation", ""),
            "has_face": int(data.get("has_face", 0)),
        }

    def extract_text(self, frames: list[Image.Image]) -> str:
        prompt = """
Extract all text visible on screen in these video frames. Concatenate unique phrases, preserving the original language. Remove duplicates. Return plain text only; if no text is visible, return an empty string.
"""
        text = self.client.analyze(frames, prompt)
        return str(text).strip() if text else ""

    def detect_face_position(self, frame: Image.Image) -> str:
        prompt = """
Look at this frame from a short video. Where is the main person's face located vertically?
Answer with exactly one word: top, center, or bottom. If no face is visible, answer bottom.
"""
        result = self.client.analyze([frame], prompt)
        position = str(result).strip().lower()
        if position in ("top", "center", "bottom"):
            return position
        return "bottom"
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_analyzer.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/analyzer.py tests/test_analyzer.py
git commit -m "feat: add video analyzer with gemini description, OCR and face position"
```

---

### Task 6: Indexer

**Files:**
- Create: `src/indexer.py`
- Create: `tests/test_indexer.py`

**Interfaces:**
- Consumes: `VideoAnalyzer`, `VideoRepository`, `ffmpeg_utils`
- Produces: `index_videos_folder(videos_dir: str, analyzer, repo) -> int` returns number of videos indexed.

- [ ] **Step 1: Write the failing test**

Create `tests/test_indexer.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.indexer import index_videos_folder


@patch("src.indexer.open_image")
@patch("src.indexer.ffmpeg_utils.extract_frames", return_value=["frame1.jpg", "frame2.jpg", "frame3.jpg"])
@patch("src.indexer.ffmpeg_utils.get_duration", return_value=10.0)
def test_index_videos_folder(mock_duration, mock_extract, mock_open, tmp_path):
    video = tmp_path / "sample.MP4"
    video.write_text("dummy")

    analyzer = MagicMock()
    analyzer.describe.return_value = {
        "description": "Test video",
        "themes": "test",
        "orientation": "portrait",
        "has_face": 1,
    }

    repo = MagicMock()
    repo.upsert = MagicMock()

    count = index_videos_folder(str(tmp_path), analyzer, repo)
    assert count == 1
    repo.upsert.assert_called_once()
    call_args = repo.upsert.call_args[0][0]
    assert call_args["filename"] == "sample.MP4"
    assert call_args["duration_seconds"] == 10.0
```

Run:

```bash
python -m pytest tests/test_indexer.py -v
```

Expected: FAIL.

- [ ] **Step 2: Implement `src/indexer.py`**

```python
from pathlib import Path
from src.analyzer import VideoAnalyzer
from src.database import VideoRepository
from src import ffmpeg_utils


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def _list_video_files(directory: str) -> list[Path]:
    path = Path(directory)
    if not path.exists():
        return []
    files = [p for p in path.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS]
    return sorted(files)


def index_videos_folder(
    videos_dir: str,
    analyzer: VideoAnalyzer,
    repo: VideoRepository,
    frames_per_video: int = 3,
    frames_output_dir: str = "./data/frames",
) -> int:
    files = _list_video_files(videos_dir)
    indexed = 0
    for file_path in files:
        duration = ffmpeg_utils.get_duration(str(file_path))
        timestamps = ffmpeg_utils.calculate_frame_timestamps(duration, frames_per_video)
        frame_paths = ffmpeg_utils.extract_frames(str(file_path), timestamps, frames_output_dir)

        images = [open_image(p) for p in frame_paths]
        try:
            description = analyzer.describe(images)
        finally:
            for img in images:
                img.close()

        repo.upsert({
            "path": str(file_path),
            "filename": file_path.name,
            "description": description.get("description", ""),
            "themes": description.get("themes", ""),
            "orientation": description.get("orientation", ""),
            "duration_seconds": duration,
            "has_face": int(description.get("has_face", 0)),
            "frame_paths": frame_paths,
        })
        indexed += 1
    return indexed


def open_image(path: str):
    from PIL import Image
    return Image.open(path)
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_indexer.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/indexer.py tests/test_indexer.py
git commit -m "feat: add indexer to analyze and persist local videos"
```

---

### Task 7: Reels Downloader

**Files:**
- Create: `src/downloader.py`
- Create: `tests/test_downloader.py`

**Interfaces:**
- Consumes: none
- Produces: `download_reels(url: str, output_dir: str) -> str` returns local file path.

- [ ] **Step 1: Write the failing test**

Create `tests/test_downloader.py`:

```python
from unittest.mock import patch, MagicMock
from src.downloader import _sanitize_filename, download_reels


def test_sanitize_filename():
    assert _sanitize_filename("hello/world:test.mp4") == "hello_world_test.mp4"


@patch("src.downloader.yt_dlp.YoutubeDL")
def test_download_calls_youtube_dl(mock_ydl_class):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl
    download_reels("https://instagram.com/reel/abc", "./downloads")
    mock_ydl.download.assert_called_once()
```

Run:

```bash
python -m pytest tests/test_downloader.py -v
```

Expected: FAIL.

- [ ] **Step 2: Implement `src/downloader.py`**

```python
import re
from pathlib import Path
from yt_dlp import YoutubeDL


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-_.]', '_', name)


def download_reels(url: str, output_dir: str) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    template = str(output_path / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": template,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id", "reels")
        ext = info.get("ext", "mp4")
        downloaded = output_path / f"{video_id}.{ext}"
    return str(downloaded)
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_downloader.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/downloader.py tests/test_downloader.py
git commit -m "feat: add reels downloader using yt-dlp"
```

---

### Task 8: Matcher

**Files:**
- Create: `src/matcher.py`
- Create: `tests/test_matcher.py`

**Interfaces:**
- Consumes: `VideoAnalyzer`/`GeminiClient`
- Produces: `Matcher.rank_candidates(reference_description, candidates) -> list[dict]`, `Matcher.select_best_video(reference_frames, top_candidates) -> dict[str, Any]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_matcher.py`:

```python
from unittest.mock import MagicMock
from src.matcher import Matcher


def test_rank_candidates():
    mock_client = MagicMock()
    mock_client.analyze.return_value = '{"ranking": [{"path": "b.mp4", "reason": "similar beach theme"}, {"path": "a.mp4"}]}'
    matcher = Matcher(mock_client)
    candidates = [
        {"path": "a.mp4", "description": "City"},
        {"path": "b.mp4", "description": "Beach"},
    ]
    result = matcher.rank_candidates("Beach vibes", candidates)
    assert result[0]["path"] == "b.mp4"


def test_select_best_video():
    mock_client = MagicMock()
    mock_client.analyze.return_value = '{"best_path": "b.mp4", "reason": "colors match"}'
    matcher = Matcher(mock_client)
    from PIL import Image
    ref_frames = [Image.new("RGB", (10, 10))]
    top = [{"path": "a.mp4", "frame_paths": []}, {"path": "b.mp4", "frame_paths": []}]
    winner = matcher.select_best_video(ref_frames, top)
    assert winner["path"] == "b.mp4"
```

Run:

```bash
python -m pytest tests/test_matcher.py -v
```

Expected: FAIL.

- [ ] **Step 2: Implement `src/matcher.py`**

```python
import json
from typing import Any
from PIL import Image
from src.gemini_client import GeminiClient


class Matcher:
    def __init__(self, client: GeminiClient):
        self.client = client

    def rank_candidates(
        self,
        reference_description: str,
        candidates: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        prompt = f"""
Reference video description: {reference_description}

Local videos:
"""
        for idx, c in enumerate(candidates, 1):
            prompt += f"{idx}. Path: {c['path']}\nDescription: {c['description']}\nThemes: {c.get('themes', '')}\nOrientation: {c.get('orientation', '')}\nDuration: {c.get('duration_seconds', 0)}s\n\n"

        prompt += f"""
Rank the {top_k} local videos that best match the reference video in terms of theme, content, style and orientation.
Return valid JSON only, with a field "ranking" containing objects with "path" and "reason".
"""
        schema = {
            "type": "object",
            "properties": {
                "ranking": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["path", "reason"],
                    },
                }
            },
            "required": ["ranking"],
        }
        raw = self.client.analyze([], prompt, response_schema=schema)
        data = json.loads(raw) if isinstance(raw, str) else raw
        ranking = data.get("ranking", [])
        paths = [r["path"] for r in ranking]
        ordered = [c for p in paths for c in candidates if c["path"] == p]
        return ordered[:top_k]

    def select_best_video(
        self,
        reference_frames: list[Image.Image],
        top_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt = """
You are choosing the best local video to replace the visual content of a Reels reference while keeping its audio and text.
Look at the reference frames and the frames of the candidate videos below, then choose the candidate whose visual style, theme and energy match the reference most.

Return valid JSON only with fields "best_path" and "reason".
"""
        schema = {
            "type": "object",
            "properties": {
                "best_path": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["best_path", "reason"],
        }
        images = list(reference_frames)
        for c in top_candidates:
            for fp in c.get("frame_paths", [])[:3]:
                images.append(Image.open(fp))

        raw = self.client.analyze(images, prompt, response_schema=schema)
        data = json.loads(raw) if isinstance(raw, str) else raw
        best_path = data.get("best_path")
        for c in top_candidates:
            if c["path"] == best_path:
                c["selection_reason"] = data.get("reason", "")
                return c
        # Fallback to first candidate
        return top_candidates[0]
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_matcher.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/matcher.py tests/test_matcher.py
git commit -m "feat: add hybrid matcher for local video selection"
```

---

### Task 9: Video Processor

**Files:**
- Create: `src/video_processor.py`
- Create: `tests/test_video_processor.py`

**Interfaces:**
- Consumes: `ffmpeg_utils`
- Produces: `VideoProcessor.extract_audio(...) -> str`, `VideoProcessor.adjust_duration(...) -> str`, `VideoProcessor.render_final_video(...) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_video_processor.py`:

```python
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.video_processor import VideoProcessor


def test_extract_audio_builds_command():
    with patch("src.video_processor.ffmpeg_utils.run_ffmpeg") as mock_run:
        vp = VideoProcessor()
        vp.extract_audio("ref.mp4", "out/audio.aac")
    mock_run.assert_called_once()


def test_adjust_duration_for_trim():
    with patch("src.video_processor.ffmpeg_utils.run_ffmpeg") as mock_run, \
         patch("src.video_processor.ffmpeg_utils.get_duration", return_value=10.0):
        vp = VideoProcessor()
        result = vp.adjust_duration("local.mp4", 5.0, "out/adjusted.mp4")
    assert "local.mp4" in mock_run.call_args[0][0]
    assert "5.0" in mock_run.call_args[0][0]


def test_render_final_video():
    with patch("src.video_processor.ffmpeg_utils.run_ffmpeg") as mock_run:
        vp = VideoProcessor()
        vp.render_final_video("adjusted.mp4", "audio.aac", "hello", "bottom", "out/final.mp4")
    args = mock_run.call_args[0][0]
    assert any("drawtext" in str(a) for a in args)
```

Run:

```bash
python -m pytest tests/test_video_processor.py -v
```

Expected: FAIL.

- [ ] **Step 2: Implement `src/video_processor.py`**

```python
import math
import os
from pathlib import Path
from src import ffmpeg_utils


class VideoProcessor:
    def __init__(self, ffmpeg_path: str | None = None):
        self.ffmpeg_path = ffmpeg_path

    def extract_audio(self, video_path: str, output_audio_path: str) -> str:
        Path(output_audio_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_utils.run_ffmpeg([
            "-y",
            "-i", video_path,
            "-vn",
            "-c:a", "aac",
            "-b:a", "192k",
            output_audio_path,
        ])
        return output_audio_path

    def adjust_duration(self, video_path: str, target_duration: float, output_path: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        current_duration = ffmpeg_utils.get_duration(video_path)

        if current_duration < target_duration:
            loops = math.ceil(target_duration / current_duration)
            concat_list_path = str(Path(output_path).parent / "concat_list.txt")
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for _ in range(loops):
                    f.write(f"file '{video_path.replace(chr(39), chr(39)+chr(39))}'\n")
            ffmpeg_utils.run_ffmpeg([
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                "-t", str(target_duration),
                output_path,
            ])
            os.remove(concat_list_path)
        else:
            ffmpeg_utils.run_ffmpeg([
                "-y",
                "-i", video_path,
                "-c", "copy",
                "-t", str(target_duration),
                output_path,
            ])
        return output_path

    def render_final_video(
        self,
        video_path: str,
        audio_path: str,
        text: str,
        face_position: str,
        output_path: str,
        font_path: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        vertical_position = "y=(h-text_h)-120" if face_position in ("top", "center") else "y=120"
        safe_text = text.replace("'", "'\\''").replace(":", "\\:")
        filter_str = (
            f"drawtext=fontfile={font_path}:"
            f"text='{safe_text}':"
            "fontcolor=white:fontsize=72:"
            "box=1:boxcolor=black@0.6:boxborderw=12:"
            "x=(w-text_w)/2:" + vertical_position
        )

        ffmpeg_utils.run_ffmpeg([
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ])
        return output_path
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_video_processor.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/video_processor.py tests/test_video_processor.py
git commit -m "feat: add video processor for audio, loop/trim and overlay"
```

---

### Task 10: CLI Orchestrator

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

**Interfaces:**
- Consumes: all previous modules
- Produces: CLI commands `index` and `clone <url>`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_main.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from src import main


def test_cli_index_parses():
    with patch("src.main.index_command") as mock_index:
        main.main(["index"])
    mock_index.assert_called_once()


def test_cli_clone_parses():
    with patch("src.main.clone_command") as mock_clone:
        main.main(["clone", "https://instagram.com/reel/abc"])
    mock_clone.assert_called_once()
    args, _ = mock_clone.call_args
    assert args[0] == "https://instagram.com/reel/abc"
```

Run:

```bash
python -m pytest tests/test_main.py -v
```

Expected: FAIL.

- [ ] **Step 2: Implement `src/main.py`**

```python
import argparse
import logging
import sys
from pathlib import Path

from src.config import get_settings
from src.database import VideoRepository
from src.gemini_client import GeminiClient
from src.analyzer import VideoAnalyzer
from src.indexer import index_videos_folder
from src.downloader import download_reels
from src.matcher import Matcher
from src.video_processor import VideoProcessor


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def index_command(args: argparse.Namespace):
    settings = get_settings()
    setup_logging(settings.log_level)
    repo = VideoRepository(str(Path(settings.data_dir) / "videos.db"))
    repo.ensure_schema()
    client = GeminiClient(settings.gemini_api_key, settings.gemini_model)
    analyzer = VideoAnalyzer(client)
    count = index_videos_folder(
        settings.local_videos_dir,
        analyzer,
        repo,
        frames_per_video=settings.frames_per_video,
        frames_output_dir=str(Path(settings.data_dir) / "frames"),
    )
    print(f"Indexed {count} videos from {settings.local_videos_dir}")


def clone_command(args: argparse.Namespace):
    settings = get_settings()
    setup_logging(settings.log_level)

    repo = VideoRepository(str(Path(settings.data_dir) / "videos.db"))
    repo.ensure_schema()
    candidates = repo.get_all()
    if not candidates:
        print("No local videos indexed. Run 'python -m src.main index' first.")
        sys.exit(1)

    client = GeminiClient(settings.gemini_api_key, settings.gemini_model)
    analyzer = VideoAnalyzer(client)

    print(f"Downloading reference Reels from {args.url}...")
    reference_path = download_reels(args.url, str(Path(settings.data_dir) / "downloads"))

    print("Analyzing reference video...")
    from src import ffmpeg_utils
    from PIL import Image

    ref_duration = ffmpeg_utils.get_duration(reference_path)
    ref_timestamps = ffmpeg_utils.calculate_frame_timestamps(ref_duration, settings.frames_per_video)
    ref_frame_paths = ffmpeg_utils.extract_frames(reference_path, ref_timestamps, str(Path(settings.data_dir) / "frames"))
    ref_frames = [Image.open(p) for p in ref_frame_paths]

    ref_description = analyzer.describe(ref_frames)
    on_screen_text = analyzer.extract_text(ref_frames)
    print(f"Extracted text: {on_screen_text}")

    print("Matching local videos...")
    matcher = Matcher(client)
    ranked = matcher.rank_candidates(ref_description["description"], candidates)
    if not ranked:
        print("No suitable local video found.")
        sys.exit(1)

    winner = matcher.select_best_video(ref_frames, ranked[:3])
    print(f"Selected local video: {winner['path']}")

    processor = VideoProcessor()
    audio_path = processor.extract_audio(reference_path, str(Path(settings.data_dir) / "audio.aac"))
    adjusted_path = processor.adjust_duration(
        winner["path"],
        ref_duration,
        str(Path(settings.data_dir) / "adjusted.mp4"),
    )

    middle_frame = Image.open(winner["frame_paths"][len(winner["frame_paths"]) // 2])
    face_position = analyzer.detect_face_position(middle_frame)

    output_name = f"{Path(reference_path).stem}_final.mp4"
    output_path = Path(args.output_dir or Path(settings.data_dir) / "output") / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_path = processor.render_final_video(
        adjusted_path,
        audio_path,
        on_screen_text or "",
        face_position,
        str(output_path),
    )
    print(f"Done: {final_path}")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Reels Cloner MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index local videos")
    index_parser.set_defaults(func=index_command)

    clone_parser = subparsers.add_parser("clone", help="Clone a Reels using a local video")
    clone_parser.add_argument("url", help="Instagram Reels URL")
    clone_parser.add_argument("--output-dir", help="Directory for final video")
    clone_parser.set_defaults(func=clone_command)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_main.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add CLI orchestrator with index and clone commands"
```

---

### Task 11: Docker setup

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

**Interfaces:**
- Consumes: all previous modules
- Produces: runnable container with FFmpeg, Python deps and source code.

- [ ] **Step 1: Write the failing test**

No automated test required. Validate with:

```bash
docker compose build
```

Expected: FAIL because files do not exist yet.

- [ ] **Step 2: Implement `Dockerfile`**

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

CMD ["python", "-m", "src.main", "index"]
```

- [ ] **Step 3: Implement `docker-compose.yml`**

```yaml
version: "3.9"

services:
  reels-cloner:
    build: .
    env_file:
      - .env
    environment:
      - LOCAL_VIDEOS_DIR=/app/videos
    volumes:
      - ./data:/app/data
      - "C:\\Users\\victor.felix\\Pictures\\reels-turbo\\Vídeos do fuga:/app/videos:ro"
    command: ["python", "-m", "src.main", "clone", "${REELS_URL}"]
    # Fallback command when REELS_URL is not set:
    # command: ["python", "-m", "src.main", "index"]
```

- [ ] **Step 4: Validate build**

```bash
docker compose build
```

Expected: image builds successfully (may take a few minutes).

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "chore: add Dockerfile and docker-compose setup"
```

---

### Task 12: Documentation

**Files:**
- Create: `README.md`

**Interfaces:**
- None (documentation).

- [ ] **Step 1: Write `README.md`**

```markdown
# Reels Cloner MVP

Automatiza a clonagem de Reels: baixa um vídeo de referência do Instagram, escolhe o melhor vídeo local da sua pasta e gera um novo vídeo com o áudio e texto do original.

## Requisitos

- Python 3.11+
- FFmpeg instalado e disponível no PATH
- Conta e chave de API do Google Gemini

## Instalação

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha:

```bash
GEMINI_API_KEY=sua_chave_aqui
```

## Uso

1. Indexe seus vídeos locais (análise feita apenas uma vez, reindexa somente quando novos vídeos são adicionados):

```bash
python -m src.main index
```

2. Clone um Reels a partir da URL:

```bash
python -m src.main clone "https://www.instagram.com/reel/ABC123/"
```

O vídeo final será salvo em `data/output/`.

## Docker

```bash
docker compose build
# Indexar localmente dentro do container:
docker compose run --rm reels-cloner python -m src.main index
# Clonar (defina REELS_URL no .env):
docker compose up
```

## Estrutura

- `src/main.py` — CLI
- `src/indexer.py` — indexação dos vídeos locais
- `src/downloader.py` — download do Reels com yt-dlp
- `src/analyzer.py` — descrição, OCR e detecção de rosto via Gemini
- `src/matcher.py` — seleção do melhor vídeo local
- `src/video_processor.py` — manipulação de áudio/vídeo com FFmpeg
- `src/database.py` — metadados no SQLite

## Limitações do MVP

- O texto do Reels é aplicado como overlay estático no vídeo final.
- A integração com WhatsApp/Wuzapi é um próximo passo.
- Escolha final do vídeo local é automática, sem revisão do usuário.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage"
```

---

## Self-Review

### Spec coverage

- RF01: Task 10 (`clone` CLI command).
- RF02: Task 7 (`download_reels`).
- RF03: Task 4 (`calculate_frame_timestamps` + `extract_frames`).
- RF04: Task 5 (`describe`).
- RF05: Task 3 (`VideoRepository`).
- RF06: Task 6 (`index_videos_folder` upserts by path, so re-running `index` updates existing entries and adds new ones without losing data).
- RF07: Task 8 (`rank_candidates`).
- RF08: Task 8 (`select_best_video`).
- RF09: Task 5 (`extract_text`).
- RF10: Task 9 (`adjust_duration`).
- RF11: Task 5 (`detect_face_position`).
- RF12: Task 9 + 10 (`render_final_video`).

### Placeholder scan

- No placeholders or TODOs remain in code blocks.
- No vague steps such as "add error handling" without code.

### Type consistency

- `GeminiClient.analyze` returns `str | dict` consistently.
- `VideoRepository.upsert` expects keys defined in the schema.
- `VideoRepository.get_all` / `get_by_path` parse `frame_paths` from JSON string to list before returning.
- `Matcher.rank_candidates` outputs list of candidate dicts consumed by `select_best_video`.
- `VideoProcessor` methods receive and return file paths as strings.
