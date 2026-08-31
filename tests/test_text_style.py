from src.text_style import (
    DEFAULT_TEXT_STYLE,
    font_path_for,
    merge_user_style,
    normalize_text_style,
    text_style_options,
)


def test_normalize_text_style_defaults():
    assert normalize_text_style(None) == DEFAULT_TEXT_STYLE


def test_normalize_text_style_keeps_valid_values():
    style = {"font": "anton", "color": "#0066FF", "background": "white"}
    assert normalize_text_style(style) == style


def test_normalize_text_style_rejects_invalid_values():
    style = {"font": "comic-sans", "color": "not-a-color", "background": "transparent"}
    assert normalize_text_style(style) == DEFAULT_TEXT_STYLE


def test_merge_user_style_overrides_ai_style():
    ai_style = {
        "font_color": "black",
        "has_background_box": True,
        "font_size_relative": "large",
        "position_vertical": "bottom",
    }
    user_style = {"font": "montserrat", "color": "#FFD400", "background": "none"}
    merged = merge_user_style(user_style, ai_style)

    assert merged["font_color"] == "#FFD400"
    assert merged["background_mode"] == "none"
    assert merged["font_id"] == "montserrat"
    assert merged["font_size_relative"] == "large"
    assert merged["position_vertical"] == "bottom"


def test_font_path_for_system_is_empty():
    assert font_path_for("system") == ""


def test_text_style_options_exposes_catalogs():
    options = text_style_options()
    assert any(font["id"] == "montserrat" for font in options["fonts"])
    assert any(color["id"] == "white" for color in options["colors"])
    assert any(background["id"] == "black" for background in options["backgrounds"])
