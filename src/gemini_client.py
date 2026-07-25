from io import BytesIO
import time
import logging
from typing import Any
from PIL import Image
from google.genai import Client
from google.genai.types import Content, Part

logger = logging.getLogger(__name__)


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
        parts: list[Part] = [Part.from_text(text=prompt)]
        for image in images:
            parts.append(self._image_part(image))

        config = {"temperature": 0.3, "max_output_tokens": 2048}
        if response_schema:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_schema

        max_retries = 4
        delay = 2.0  # Tempo inicial em segundos
        
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[Content(role="user", parts=parts)],
                    config=config,
                )
                text = response.text or ""
                if response_schema:
                    text = _repair_json_string(text)
                return text
            except Exception as e:
                err_str = str(e)
                # Verifica se é um erro temporário (503, 429, limites de quota, picos de demanda ou indisponibilidade)
                is_transient = any(
                    code in err_str.lower()
                    for code in ["503", "429", "unavailable", "resourceexhausted", "high demand", "temporary", "limit"]
                )
                
                if is_transient and attempt < max_retries:
                    logger.warning(
                        f"Erro temporário na API do Gemini (tentativa {attempt}/{max_retries}): {e}. "
                        f"Tentando novamente em {delay} segundos..."
                    )
                    time.sleep(delay)
                    delay *= 2.0  # Backoff exponencial: 2s, 4s, 8s...
                else:
                    # Se esgotar as tentativas ou for um erro permanente (ex: chave inválida), propaga o erro
                    raise e
        if response_schema:
            text = _repair_json_string(text)
        return text

    def _image_part(self, image: Image.Image) -> Part:
        if image.mode != "RGB":
            image = image.convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        return Part.from_bytes(data=buffer.getvalue(), mime_type="image/jpeg")


def _repair_json_string(s: str) -> str:
    s = s.strip()
    if s.startswith("```json"):
        s = s[7:]
    if s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    s = s.strip()

    # Step 1: Escape non-structural (inner) double quotes
    chars = list(s)
    n = len(chars)
    for i in range(n):
        if chars[i] == '"':
            # Check if this quote is structural
            left_neighbor = None
            for j in range(i - 1, -1, -1):
                if s[j] not in (' ', '\t', '\n', '\r'):
                    left_neighbor = s[j]
                    break
            right_neighbor = None
            for j in range(i + 1, n):
                if s[j] not in (' ', '\t', '\n', '\r'):
                    right_neighbor = s[j]
                    break
            
            is_structural = (
                (left_neighbor in ('{', '[', ',', ':')) or
                (right_neighbor in ('}', ']', ',', ':'))
            )
            if i == 0 or i == n - 1:
                is_structural = True
                
            if not is_structural:
                chars[i] = '\\"'
    s = "".join(chars)

    # Step 2: Escape physical newlines inside string values
    in_string = False
    escaped = False
    result = []
    for char in s:
        if char == '"' and not escaped:
            in_string = not in_string
            result.append(char)
        elif char == '\\' and in_string and not escaped:
            escaped = True
            result.append(char)
        elif in_string:
            escaped = False
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                pass
            else:
                result.append(char)
        else:
            escaped = False
            result.append(char)
    return "".join(result)
