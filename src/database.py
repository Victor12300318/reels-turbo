import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None


class VideoRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.is_postgres = db_path.startswith("postgres://") or db_path.startswith("postgresql://")
        if not self.is_postgres and db_path:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        if self.is_postgres:
            if not psycopg:
                raise RuntimeError("psycopg package is required for PostgreSQL connections.")
            return psycopg.connect(self.db_path, row_factory=dict_row, autocommit=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ph(self, count: int = 1) -> str:
        """Returns parameter placeholder(s) for SQL queries."""
        ph = "%s" if self.is_postgres else "?"
        if count == 1:
            return ph
        return ", ".join([ph] * count)

    def ensure_schema(self) -> None:
        conn = self._connect()
        try:
            if self.is_postgres:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        password_salt TEXT,
                        api_key TEXT UNIQUE NOT NULL,
                        is_admin INTEGER DEFAULT 0,
                        is_active INTEGER DEFAULT 1,
                        instagram_account_id TEXT,
                        instagram_access_token TEXT,
                        default_caption_suffix TEXT,
                        share_to_feed INTEGER DEFAULT 0,
                        default_post_interval_hours INTEGER DEFAULT 3,
                        created_at TEXT NOT NULL
                    )
                """)
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_salt TEXT")
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1")
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS instagram_account_id TEXT")
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS instagram_access_token TEXT")
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS default_caption_suffix TEXT")
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS share_to_feed INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS default_post_interval_hours INTEGER DEFAULT 3")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS videos (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT,
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
                conn.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS user_id TEXT")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        url TEXT NOT NULL,
                        status TEXT NOT NULL,
                        progress INTEGER DEFAULT 0,
                        output_path TEXT,
                        error TEXT,
                        caption TEXT,
                        scheduled_at TEXT,
                        posted_at TEXT,
                        share_to_feed INTEGER DEFAULT 0,
                        original_s3_url TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS user_id TEXT")
                conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS caption TEXT")
                conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS scheduled_at TEXT")
                conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS posted_at TEXT")
                conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS share_to_feed INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS original_s3_url TEXT")
            else:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id TEXT PRIMARY KEY,
                            email TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            password_salt TEXT,
                            api_key TEXT UNIQUE NOT NULL,
                            is_admin INTEGER DEFAULT 0,
                            is_active INTEGER DEFAULT 1,
                            instagram_account_id TEXT,
                            instagram_access_token TEXT,
                            default_caption_suffix TEXT,
                            share_to_feed INTEGER DEFAULT 0,
                            default_post_interval_hours INTEGER DEFAULT 3,
                            created_at TEXT NOT NULL
                        )
                    """)
                    cursor = conn.execute("PRAGMA table_info(users)")
                    cols = [row[1] for row in cursor.fetchall()]
                    if "password_salt" not in cols:
                        conn.execute("ALTER TABLE users ADD COLUMN password_salt TEXT")
                    if "is_admin" not in cols:
                        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
                    if "is_active" not in cols:
                        conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
                    if "instagram_account_id" not in cols:
                        conn.execute("ALTER TABLE users ADD COLUMN instagram_account_id TEXT")
                    if "instagram_access_token" not in cols:
                        conn.execute("ALTER TABLE users ADD COLUMN instagram_access_token TEXT")
                    if "default_caption_suffix" not in cols:
                        conn.execute("ALTER TABLE users ADD COLUMN default_caption_suffix TEXT")
                    if "share_to_feed" not in cols:
                        conn.execute("ALTER TABLE users ADD COLUMN share_to_feed INTEGER DEFAULT 0")
                    if "default_post_interval_hours" not in cols:
                        conn.execute("ALTER TABLE users ADD COLUMN default_post_interval_hours INTEGER DEFAULT 3")

                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS videos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id TEXT,
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
                    cursor = conn.execute("PRAGMA table_info(videos)")
                    cols = [row[1] for row in cursor.fetchall()]
                    if "user_id" not in cols:
                        conn.execute("ALTER TABLE videos ADD COLUMN user_id TEXT")

                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS jobs (
                            id TEXT PRIMARY KEY,
                            user_id TEXT,
                            url TEXT NOT NULL,
                            status TEXT NOT NULL,
                            progress INTEGER DEFAULT 0,
                            output_path TEXT,
                            error TEXT,
                            caption TEXT,
                            scheduled_at TEXT,
                            posted_at TEXT,
                            share_to_feed INTEGER DEFAULT 0,
                            original_s3_url TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                    """)
                    cursor = conn.execute("PRAGMA table_info(jobs)")
                    cols = [row[1] for row in cursor.fetchall()]
                    if "user_id" not in cols:
                        conn.execute("ALTER TABLE jobs ADD COLUMN user_id TEXT")
                    if "caption" not in cols:
                        conn.execute("ALTER TABLE jobs ADD COLUMN caption TEXT")
                    if "scheduled_at" not in cols:
                        conn.execute("ALTER TABLE jobs ADD COLUMN scheduled_at TEXT")
                    if "posted_at" not in cols:
                        conn.execute("ALTER TABLE jobs ADD COLUMN posted_at TEXT")
                    if "share_to_feed" not in cols:
                        conn.execute("ALTER TABLE jobs ADD COLUMN share_to_feed INTEGER DEFAULT 0")
                    if "original_s3_url" not in cols:
                        conn.execute("ALTER TABLE jobs ADD COLUMN original_s3_url TEXT")
        finally:
            conn.close()

    # --- USER OPERATIONS ---
    def create_user(
        self,
        email: str,
        password_hash: str,
        api_key: str,
        password_salt: str = "",
        is_admin: int = 0,
        is_active: int = 1,
        user_id: str | None = None
    ) -> dict[str, Any]:
        uid = user_id or str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        ph = self._ph(8)
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"INSERT INTO users (id, email, password_hash, password_salt, api_key, is_admin, is_active, created_at) VALUES ({ph})",
                    (uid, email, password_hash, password_salt, api_key, is_admin, is_active, created_at),
                )
        finally:
            conn.close()
        return {
            "id": uid, "email": email, "api_key": api_key, "password_salt": password_salt,
            "is_admin": is_admin, "is_active": is_active, "created_at": created_at
        }

    def get_all_users(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cursor = conn.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_user_password(self, user_id: str, password_hash: str, password_salt: str) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE users SET password_hash = {self._ph(1)}, password_salt = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (password_hash, password_salt, user_id)
                )
        finally:
            conn.close()

    def update_user_credentials(
        self, user_id: str, email: str, password_hash: str, password_salt: str, is_admin: int = 1, is_active: int = 1
    ) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE users SET email = {self._ph(1)}, password_hash = {self._ph(1)}, password_salt = {self._ph(1)}, is_admin = {self._ph(1)}, is_active = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (email, password_hash, password_salt, is_admin, is_active, user_id)
                )
        finally:
            conn.close()

    def regenerate_user_api_key(self, user_id: str, new_api_key: str) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE users SET api_key = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (new_api_key, user_id)
                )
        finally:
            conn.close()

    def toggle_user_active(self, user_id: str, is_active: int) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE users SET is_active = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (is_active, user_id)
                )
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        ph = self._ph(1)
        conn = self._connect()
        try:
            cursor = conn.execute(f"SELECT * FROM users WHERE email = {ph}", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_by_api_key(self, api_key: str) -> dict[str, Any] | None:
        ph = self._ph(1)
        conn = self._connect()
        try:
            cursor = conn.execute(f"SELECT * FROM users WHERE api_key = {ph}", (api_key,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        ph = self._ph(1)
        conn = self._connect()
        try:
            cursor = conn.execute(f"SELECT * FROM users WHERE id = {ph}", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_user_instagram_credentials(self, user_id: str, account_id: str, access_token: str) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE users SET instagram_account_id = {self._ph(1)}, instagram_access_token = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (account_id, access_token, user_id)
                )
        finally:
            conn.close()

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

    # --- VIDEO OPERATIONS ---
    def upsert(self, video: dict[str, Any], user_id: str | None = None) -> None:
        frame_paths = video.get("frame_paths", [])
        if isinstance(frame_paths, list):
            frame_paths = json.dumps(frame_paths)
        
        ph = self._ph(10)
        conn = self._connect()
        try:
            with conn:
                conn.execute(f"""
                    INSERT INTO videos (
                        path, filename, description, themes, orientation,
                        duration_seconds, has_face, frame_paths, updated_at, user_id
                    ) VALUES ({ph})
                    ON CONFLICT(path) DO UPDATE SET
                        filename=EXCLUDED.filename,
                        description=EXCLUDED.description,
                        themes=EXCLUDED.themes,
                        orientation=EXCLUDED.orientation,
                        duration_seconds=EXCLUDED.duration_seconds,
                        has_face=EXCLUDED.has_face,
                        frame_paths=EXCLUDED.frame_paths,
                        updated_at=EXCLUDED.updated_at,
                        user_id=EXCLUDED.user_id
                """, (
                    video["path"],
                    video["filename"],
                    video.get("description", ""),
                    video.get("themes", ""),
                    video.get("orientation", ""),
                    video.get("duration_seconds", 0.0),
                    int(video.get("has_face", 0)),
                    frame_paths,
                    datetime.now(timezone.utc).isoformat(),
                    user_id or video.get("user_id"),
                ))
        finally:
            conn.close()

    def get_all(self, user_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            if user_id:
                ph = self._ph(1)
                cursor = conn.execute(f"SELECT * FROM videos WHERE user_id = {ph}", (user_id,))
            else:
                cursor = conn.execute("SELECT * FROM videos")
            rows = cursor.fetchall()
            return [_parse_row(r) for r in rows]
        finally:
            conn.close()

    def get_by_path(self, path: str) -> dict[str, Any] | None:
        ph = self._ph(1)
        conn = self._connect()
        try:
            cursor = conn.execute(f"SELECT * FROM videos WHERE path = {ph}", (path,))
            row = cursor.fetchone()
            return _parse_row(row) if row else None
        finally:
            conn.close()

    def delete_video(self, video_id: int, user_id: str) -> None:
        ph = self._ph(2)
        conn = self._connect()
        try:
            with conn:
                conn.execute(f"DELETE FROM videos WHERE id = {self._ph(1)} AND user_id = {self._ph(1)}", (video_id, user_id))
        finally:
            conn.close()

    # --- JOB OPERATIONS ---
    def create_job(self, user_id: str, url: str) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        ph = self._ph(9)
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"INSERT INTO jobs (id, user_id, url, status, progress, output_path, error, created_at, updated_at) VALUES ({ph})",
                    (job_id, user_id, url, "pending", 0, "", "", now, now)
                )
        finally:
            conn.close()
        return {
            "id": job_id, "user_id": user_id, "url": url, "status": "pending",
            "progress": 0, "output_path": "", "error": "", "created_at": now, "updated_at": now
        }

    def update_job(self, job_id: str, status: str, progress: int = 0, output_path: str = "", error: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE jobs SET status = {self._ph(1)}, progress = {self._ph(1)}, output_path = {self._ph(1)}, error = {self._ph(1)}, updated_at = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (status, progress, output_path, error, now, job_id)
                )
        finally:
            conn.close()

    def update_job_schedule(self, job_id: str, caption: str, scheduled_at: str, share_to_feed: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE jobs SET caption = {self._ph(1)}, scheduled_at = {self._ph(1)}, share_to_feed = {self._ph(1)}, status = 'scheduled', updated_at = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (caption, scheduled_at, share_to_feed, now, job_id)
                )
        finally:
            conn.close()

    def get_scheduled_jobs_due(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        ph = self._ph(1)
        conn = self._connect()
        try:
            cursor = conn.execute(f"SELECT * FROM jobs WHERE status = 'scheduled' AND scheduled_at <= {ph}", (now,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def mark_job_posted(self, job_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE jobs SET status = 'completed', posted_at = {self._ph(1)}, updated_at = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (now, now, job_id)
                )
        finally:
            conn.close()

    def update_job_original_url(self, job_id: str, original_s3_url: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    f"UPDATE jobs SET original_s3_url = {self._ph(1)}, updated_at = {self._ph(1)} WHERE id = {self._ph(1)}",
                    (original_s3_url, now, job_id)
                )
        finally:
            conn.close()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        ph = self._ph(1)
        conn = self._connect()
        try:
            cursor = conn.execute(f"SELECT * FROM jobs WHERE id = {ph}", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_jobs_by_user(self, user_id: str) -> list[dict[str, Any]]:
        ph = self._ph(1)
        conn = self._connect()
        try:
            cursor = conn.execute(f"SELECT * FROM jobs WHERE user_id = {ph} ORDER BY created_at DESC", (user_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def _parse_row(row: Any) -> dict[str, Any]:
    mapped = dict(row)
    try:
        mapped["frame_paths"] = json.loads(mapped.get("frame_paths", "[]") or "[]")
    except (json.JSONDecodeError, TypeError):
        mapped["frame_paths"] = []
    return mapped

