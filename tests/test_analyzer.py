from unittest.mock import MagicMock
from PIL import Image
from src.analyzer import VideoAnalyzer


def test_detect_face_position():
    mock_client = MagicMock()
    mock_client.analyze.return_value = "top"
    analyzer = VideoAnalyzer(mock_client)
    img = Image.new("RGB", (10, 10), color="blue")
    result = analyzer.detect_face_position(img)
    assert result == "upper"


def test_extract_text():
    mock_client = MagicMock()
    mock_client.analyze.return_value = '{"lines": ["hello", "world"]}'
    analyzer = VideoAnalyzer(mock_client)
    img = Image.new("RGB", (10, 10))
    text = analyzer.extract_text([img, img])
    assert text == "hello\nworld"


def test_describe_video():
    mock_client = MagicMock()
    mock_client.analyze.return_value = '{"description": "Beach scene", "themes": "beach,summer", "orientation": "portrait", "has_face": 0}'
    analyzer = VideoAnalyzer(mock_client)
    img = Image.new("RGB", (10, 10))
    result = analyzer.describe([img, img])
    assert result["description"] == "Beach scene"
    assert result["themes"] == "beach,summer"


def test_analyze_text_style():
    mock_client = MagicMock()
    mock_client.analyze.return_value = (
        '{"position_vertical": "bottom", "position_horizontal": "center", '
        '"font_size_relative": "large", "font_color": "white", '
        '"has_background_box": false, "justification": "center", "padding_from_edge": 10}'
    )
    analyzer = VideoAnalyzer(mock_client)
    img = Image.new("RGB", (10, 10))
    style = analyzer.analyze_text_style([img])
    assert style["position_vertical"] == "bottom"
    assert style["font_color"] == "white"
    assert not style["has_background_box"]


def test_analyze_text_style_fallback():
    mock_client = MagicMock()
    # Return faulty JSON missing comma or quote to simulate the real error reported by user
    mock_client.analyze.return_value = '{"position_vertical": "bottom" "font_color": "white"}'
    analyzer = VideoAnalyzer(mock_client)
    img = Image.new("RGB", (10, 10))
    style = analyzer.analyze_text_style([img])
    assert style["position_vertical"] == "bottom"
    assert style["font_color"] == "white"
    assert style["padding_from_edge"] == 14  # Default fallback value
