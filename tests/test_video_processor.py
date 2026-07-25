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
    args = mock_run.call_args[0][0]
    assert "local.mp4" in args
    assert "5.0" in args
    assert "-an" in args


def test_render_final_video():
    with patch("src.video_processor.ffmpeg_utils.run_ffmpeg") as mock_run, \
         patch("src.video_processor.ffmpeg_utils.get_video_dimensions", return_value=(720, 1280)):
        vp = VideoProcessor()
        vp.render_final_video("adjusted.mp4", "audio.aac", "hello world", "bottom", "out/final.mp4")
    args = mock_run.call_args[0][0]
    assert any("drawtext" in str(a) for a in args)
    assert "-map" in args


def test_wrap_text_uses_real_newlines():
    from src.video_processor import _wrap_text
    input_text = "This is a very long text that should definitely be wrapped into multiple lines."
    wrapped = _wrap_text(input_text, max_chars_per_line=30)
    assert "\n" in wrapped
    assert "\\n" not in wrapped
    lines = wrapped.split("\n")
    assert all(len(line) <= 30 for line in lines)


def test_build_drawtext_filter_retains_real_newlines():
    from src.video_processor import _build_drawtext_filter
    style = {"font_size_relative": "medium", "font_color": "white"}
    filter_str = _build_drawtext_filter(
        text="Hello world\nThis is awesome",
        style=style,
        face_position="bottom",
        video_width=720,
        video_height=1280,
        font_path="font.ttf"
    )
    assert "text='Hello world'" in filter_str
    assert "text='This is awesome'" in filter_str


def test_sanitize_text_for_ffmpeg():
    from src.video_processor import _sanitize_text_for_ffmpeg
    # Emojis and exotics should be removed, while Portuguese accents, numbers and basic punctuation should be kept
    input_text = "Olá! Tudo bem? 😂🔥 Vamos rodar 123... áéíóúç ÁÉÍÓÚÇ!"
    sanitized = _sanitize_text_for_ffmpeg(input_text)
    assert "Olá! Tudo bem? Vamos rodar 123... áéíóúç ÁÉÍÓÚÇ!" in sanitized
    assert "😂" not in sanitized
    assert "🔥" not in sanitized


