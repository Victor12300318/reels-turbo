import os
import re
from pathlib import Path
from yt_dlp import YoutubeDL
from src.config import get_settings


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-_.]', '_', name)


def download_reels(url: str, output_dir: str) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    template = str(output_path / "%(id)s.%(ext)s")

    settings = get_settings()

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": template,
        "quiet": True,
        "no_warnings": True,
        # Force IPv4 to avoid being flagged or blocked by IPv6 ranges (very common in cloud providers)
        "source_address": "0.0.0.0",
        # Impersonate standard Windows Chrome browser headers to avoid anti-bot detection
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
            "Referer": "https://www.instagram.com/",
            "Sec-Fetch-Mode": "navigate",
        }
    }

    # If the user configured an Instagram cookies file and it exists, pass it to yt-dlp
    if settings.instagram_cookies_file:
        cookies_path = Path(settings.instagram_cookies_file)
        if cookies_path.exists():
            ydl_opts["cookiefile"] = str(cookies_path)

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id", "reels")
        ext = info.get("ext", "mp4")
        downloaded = output_path / f"{video_id}.{ext}"
    return str(downloaded)
