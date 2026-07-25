import base64
from io import BytesIO
import json
import logging
import time
from typing import Any
from PIL import Image
import requests
from src.gemini_client import GeminiClient, _repair_json_string

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, api_key: str, model: str = "google/gemini-2.0-flash-001"):
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        self.api_key = api_key
        self.model = model
        self.provider_name = "openrouter"

    def analyze(
        self,
        images: list[Image.Image],
        prompt: str,
        response_schema: dict | None = None,
    ) -> str | dict[str, Any]:
        content_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        for img in images:
            if img.mode != "RGB":
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_str}"
                }
            })

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content_parts
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }

        if response_schema:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://clonify.ai",
            "X-Title": "Clonify AI",
            "Content-Type": "application/json"
        }

        max_retries = 3
        delay = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                res = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                res.raise_for_status()
                data = res.json()
                text = data["choices"][0]["message"]["content"]
                if response_schema:
                    text = _repair_json_string(text)
                return text
            except Exception as e:
                logger.warning(f"OpenRouter API attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2.0
                else:
                    raise e


def get_ai_client(repo=None):
    from src.config import get_settings
    settings = get_settings()
    if repo is None:
        from src.database import VideoRepository
        from pathlib import Path
        db_path = str(Path(settings.data_dir) / "videos.db")
        repo = VideoRepository(db_path)

    try:
        provider = repo.get_system_setting("ai_provider", "gemini")
        if provider == "openrouter":
            or_key = repo.get_system_setting("openrouter_api_key", "")
            or_model = repo.get_system_setting("openrouter_model", "google/gemini-2.0-flash-001")
            if or_key:
                return OpenRouterClient(api_key=or_key, model=or_model)
    except Exception as e:
        logger.warning(f"Could not read system settings for AI provider: {e}")

    return GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
