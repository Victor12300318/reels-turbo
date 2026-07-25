import json
import logging
from typing import Any
from PIL import Image
from src.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


def _safe_parse_json(raw: Any, default_val: Any) -> Any:
    if not raw:
        return default_val
    if not isinstance(raw, str):
        return raw
    
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"Failed to parse JSON from Gemini response: {e}. Raw content: {raw[:300]}")
        return default_val


class VideoAnalyzer:
    def __init__(self, client: GeminiClient):
        self.client = client

    def describe(self, frames: list[Image.Image]) -> dict[str, Any]:
        prompt = """
You are analyzing frames from a short-form video. Provide a structured summary:
- description: a concise paragraph of the scene, content and style. IMPORTANT: Never use double quotes (") inside this text. If you need to quote something, use single quotes (').
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
        
        default_val = {
            "description": "Short-form video",
            "themes": "reels",
            "orientation": "portrait",
            "has_face": 0
        }
        
        try:
            raw = self.client.analyze(frames, prompt, response_schema=schema)
            data = _safe_parse_json(raw, default_val)
        except Exception as e:
            logger.error(f"Error calling Gemini in describe: {e}")
            data = default_val

        return {
            "description": data.get("description", "Short-form video"),
            "themes": data.get("themes", "reels"),
            "orientation": data.get("orientation", "portrait"),
            "has_face": int(data.get("has_face", 0)),
        }

    def extract_text(self, frames: list[Image.Image]) -> str:
        prompt = """
Extract all text visible on screen in these video frames to recreate perfect captions.
Preserve the exact line breaks as shown on screen (each visible line should be a separate item).

IMPORTANT:
1. Do NOT include any emojis (like 😂, 🔥, 🚀), special icons, or non-alphanumeric icons. Emojis cannot be rendered by the video processor.
2. Focus on highly impactful, readable standard text (Latin characters, standard punctuation, numbers).
3. If there are emojis on screen, either omit them completely or convert them into standard equivalent words if they are crucial to the context.

Return valid JSON only with a single field "lines" containing an array of strings.
If no text is visible, return {"lines": []}.
"""
        schema = {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["lines"],
        }
        
        default_val = {"lines": []}
        
        try:
            raw = self.client.analyze(frames, prompt, response_schema=schema)
            data = _safe_parse_json(raw, default_val)
        except Exception as e:
            logger.error(f"Error calling Gemini in extract_text: {e}")
            data = default_val

        lines = [str(line).strip() for line in data.get("lines", []) if str(line).strip()]
        return "\n".join(lines)

    def generate_headline_fallback(self, frames: list[Image.Image], description: str) -> str:
        """
        Gera uma legenda/headline impactante em português caso nenhum texto tenha sido detectado via OCR.
        Garante que NENHUM vídeo seja renderizado sem texto na tela.
        """
        prompt = f"""
Você está analisando este vídeo cuja descrição é: "{description}".
Gere uma frase/headline curta, chamativa e viral (1 a 2 linhas em português) para ficar na tela do Reels.
IMPORTANTE:
- Não inclua emojis.
- Seja direto, engajador e atraente.
- Retorne apenas JSON com o campo "text".
"""
        schema = {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }
        try:
            raw = self.client.analyze(frames, prompt, response_schema=schema)
            data = _safe_parse_json(raw, {"text": "Confira este vídeo incrível!"})
            txt = data.get("text", "").strip()
            if txt:
                return txt
        except Exception as e:
            logger.error(f"Erro ao gerar headline de fallback: {e}")
        return "Confira esse conteúdo!"

    def detect_face_position(self, frame: Image.Image) -> str:
        prompt = """
Look at this frame from a short video. Where is the main person's face located vertically?
Answer with exactly one word: top, center, or bottom. If no face is visible, answer bottom.
"""
        try:
            result = self.client.analyze([frame], prompt)
            position = str(result).strip().lower()
            if position in ("top", "center", "bottom"):
                return position
        except Exception as e:
            logger.error(f"Error calling Gemini in detect_face_position: {e}")
        return "bottom"

    def analyze_text_style(self, frames: list[Image.Image]) -> dict[str, Any]:
        prompt = """
You are analyzing frames from a short-form video to reproduce the on-screen text style.
Look at the text visible on screen and describe its style and placement so it can be redrawn on another video of similar dimensions.
Pay close attention to how the text is wrapped, how many lines it has, its vertical/horizontal position, color, and padding.

CRITICAL INSTRUCTIONS FOR INSTAGRAM REELS SAFE-ZONES:
- When choosing 'position_vertical', prefer "center" if the original text is located in the middle.
- If the original text is placed near the top, choose "top". To avoid overlapping with top-level Instagram UI elements (Ver prévia, back button, etc.), ensure you recommend a reasonable padding 'padding_from_edge' of at least 14-16% so the text is pushed down into the safe area.
- If the original text is placed near the bottom, choose "bottom". Our rendering pipeline automatically handles a 16% safe bottom padding to clear the user info, caption, and audio tags.

Return valid JSON only with these fields:
- position_vertical: one of "top", "center", "bottom" (choose "bottom" if it's in the lower third)
- position_horizontal: one of "left", "center", "right"
- font_size_relative: one of "small" (~3.5% of video height), "medium" (~5.5%), "large" (~7.5%), "xlarge" (~9.5%)
- font_color: dominant text color. Use simple names: "white", "black", "yellow", "red", "green", "blue", "cyan", "magenta", "orange"
- has_background_box: true if the text has a solid/semi-transparent background box behind it, false otherwise
- justification: one of "left", "center", "right" based on how the text lines are aligned
- padding_from_edge: approximate padding percentage from the nearest edge (recommend 14-20% for top or bottom positions to ensure text stays clear of the Instagram interface overlays).

If no text is visible, return defaults: bottom, center, medium, white, false, center, 14.
"""
        schema = {
            "type": "object",
            "properties": {
                "position_vertical": {"type": "string"},
                "position_horizontal": {"type": "string"},
                "font_size_relative": {"type": "string"},
                "font_color": {"type": "string"},
                "has_background_box": {"type": "boolean"},
                "justification": {"type": "string"},
                "padding_from_edge": {"type": "integer"},
            },
            "required": [
                "position_vertical", "position_horizontal", "font_size_relative",
                "font_color", "has_background_box", "justification", "padding_from_edge",
            ],
        }
        
        default_val = {
            "position_vertical": "bottom",
            "position_horizontal": "center",
            "font_size_relative": "medium",
            "font_color": "white",
            "has_background_box": False,
            "justification": "center",
            "padding_from_edge": 14
        }
        
        try:
            raw = self.client.analyze(frames, prompt, response_schema=schema)
            data = _safe_parse_json(raw, default_val)
        except Exception as e:
            logger.error(f"Error calling Gemini in analyze_text_style: {e}")
            data = default_val

        return {
            "position_vertical": data.get("position_vertical", "bottom"),
            "position_horizontal": data.get("position_horizontal", "center"),
            "font_size_relative": data.get("font_size_relative", "medium"),
            "font_color": data.get("font_color", "white"),
            "has_background_box": bool(data.get("has_background_box", False)),
            "justification": data.get("justification", "center"),
            "padding_from_edge": int(data.get("padding_from_edge", 14)),
        }
