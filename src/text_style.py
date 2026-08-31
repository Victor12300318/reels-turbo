import json
import re
from pathlib import Path
from typing import Any

FONT_CATALOG = [
    {"id": "system", "label": "Padrão do sistema", "css_family": "system-ui", "file": None},
    {"id": "montserrat", "label": "Montserrat", "css_family": "Montserrat", "file": "Montserrat.ttf"},
    {"id": "anton", "label": "Anton", "css_family": "Anton", "file": "Anton-Regular.ttf"},
    {"id": "bebas_neue", "label": "Bebas Neue", "css_family": "Bebas Neue", "file": "BebasNeue-Regular.ttf"},
    {"id": "oswald", "label": "Oswald", "css_family": "Oswald", "file": "Oswald.ttf"},
    {"id": "roboto", "label": "Roboto", "css_family": "Roboto", "file": "Roboto.ttf"},
]

COLOR_CATALOG = [
    {"id": "white", "label": "Branco", "hex": "#FFFFFF"},
    {"id": "black", "label": "Preto", "hex": "#000000"},
    {"id": "yellow", "label": "Amarelo", "hex": "#FFD400"},
    {"id": "red", "label": "Vermelho", "hex": "#FF3B30"},
    {"id": "green", "label": "Verde", "hex": "#34C759"},
    {"id": "blue", "label": "Azul", "hex": "#007AFF"},
    {"id": "cyan", "label": "Ciano", "hex": "#32ADE6"},
    {"id": "magenta", "label": "Magenta", "hex": "#FF2D55"},
    {"id": "orange", "label": "Laranja", "hex": "#FF9500"},
]

BACKGROUND_CATALOG = [
    {"id": "none", "label": "Sem fundo"},
    {"id": "white", "label": "Fundo branco"},
    {"id": "black", "label": "Fundo preto"},
]

DEFAULT_TEXT_STYLE = {"font": "system", "color": "white", "background": "none"}

_HEX_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _font_ids() -> set[str]:
    return {font["id"] for font in FONT_CATALOG}


def _background_ids() -> set[str]:
    return {background["id"] for background in BACKGROUND_CATALOG}


def _color_ids() -> set[str]:
    return {color["id"] for color in COLOR_CATALOG}


def parse_text_style(raw: Any) -> dict[str, str]:
    if raw is None or raw == "":
        return dict(DEFAULT_TEXT_STYLE)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return dict(DEFAULT_TEXT_STYLE)
    if not isinstance(raw, dict):
        return dict(DEFAULT_TEXT_STYLE)
    return raw


def normalize_text_style(style: Any) -> dict[str, str]:
    raw = parse_text_style(style)
    font = str(raw.get("font") or DEFAULT_TEXT_STYLE["font"]).strip().lower()
    if font not in _font_ids():
        font = DEFAULT_TEXT_STYLE["font"]

    color = str(raw.get("color") or DEFAULT_TEXT_STYLE["color"]).strip()
    if color.startswith("#"):
        if not _HEX_PATTERN.match(color):
            color = DEFAULT_TEXT_STYLE["color"]
    else:
        color = color.lower()
        if color not in _color_ids():
            color = DEFAULT_TEXT_STYLE["color"]

    background = str(raw.get("background") or DEFAULT_TEXT_STYLE["background"]).strip().lower()
    if background not in _background_ids():
        background = DEFAULT_TEXT_STYLE["background"]

    return {"font": font, "color": color, "background": background}


def font_path_for(font_id: str) -> str:
    font = next((item for item in FONT_CATALOG if item["id"] == font_id), None)
    if not font or not font.get("file"):
        return ""
    path = Path(__file__).resolve().parents[1] / "assets" / "fonts" / font["file"]
    return str(path) if path.exists() else ""


def merge_user_style(user_style: Any, ai_style: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalize_text_style(user_style)
    ai_style = ai_style or {}
    merged = dict(ai_style)
    merged["font_color"] = normalized["color"]
    merged["background_mode"] = normalized["background"]
    merged["font_id"] = normalized["font"]
    return merged


def text_style_options() -> dict[str, Any]:
    return {
        "fonts": FONT_CATALOG,
        "colors": COLOR_CATALOG,
        "backgrounds": BACKGROUND_CATALOG,
        "default": DEFAULT_TEXT_STYLE,
    }
