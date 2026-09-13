import os
import logging
import httpx
from src.config import get_settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_MAX_CAPTION_LEN = 1024


class TelegramPublisher:
    def __init__(self):
        self.settings = get_settings()

    def publish_video(
        self,
        video_path: str,
        caption: str = "",
        bot_token: str | None = None,
        channel_id: str | None = None,
        original_url: str | None = None,
        timeout: float = 120.0,
    ) -> dict:
        token = (bot_token or self.settings.telegram_bot_token or "").strip()
        chat_id = (channel_id or self.settings.telegram_channel_id or "").strip()

        if not token:
            raise ValueError("Telegram Bot Token is required for Telegram delivery.")
        if not chat_id:
            raise ValueError("Telegram Channel ID is required for Telegram delivery.")

        # Format caption
        full_caption = caption.strip() if caption else ""
        if original_url and original_url not in full_caption:
            ref_text = f"\n\n🔗 Original: {original_url}"
            if len(full_caption) + len(ref_text) <= TELEGRAM_MAX_CAPTION_LEN:
                full_caption = f"{full_caption}{ref_text}".strip()
            elif len(ref_text) < TELEGRAM_MAX_CAPTION_LEN:
                available = TELEGRAM_MAX_CAPTION_LEN - len(ref_text) - 3
                full_caption = f"{full_caption[:available]}...{ref_text}"

        if len(full_caption) > TELEGRAM_MAX_CAPTION_LEN:
            full_caption = full_caption[: TELEGRAM_MAX_CAPTION_LEN - 3] + "..."

        url = f"{TELEGRAM_API_BASE}/bot{token}/sendVideo"
        logger.info(f"Sending video to Telegram chat/channel {chat_id}...")

        # If local file exists, stream multipart directly
        if os.path.isfile(video_path):
            file_name = os.path.basename(video_path)
            with open(video_path, "rb") as video_file:
                files = {
                    "video": (file_name, video_file, "video/mp4"),
                }
                data = {
                    "chat_id": chat_id,
                    "caption": full_caption,
                    "supports_streaming": "true",
                }
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, data=data, files=files)
        elif video_path.startswith("http://") or video_path.startswith("https://"):
            # If path is a remote URL and not a local file
            payload = {
                "chat_id": chat_id,
                "video": video_path,
                "caption": full_caption,
                "supports_streaming": True,
            }
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)
        else:
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        try:
            res_json = resp.json()
        except Exception:
            resp.raise_for_status()
            res_json = {"ok": resp.is_success}

        if not resp.is_success or not res_json.get("ok"):
            err_desc = res_json.get("description", resp.text)
            logger.error(f"Failed to send video to Telegram: {err_desc}")
            raise RuntimeError(f"Telegram Bot API error: {err_desc}")

        logger.info(f"Video sent successfully to Telegram chat {chat_id}!")
        return res_json
