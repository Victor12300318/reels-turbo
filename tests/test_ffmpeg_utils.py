from unittest.mock import patch, MagicMock
from src import ffmpeg_utils


def test_get_duration_parses_json():
    sample_json = '{"format": {"duration": "15.230000"}}'
    with patch("src.ffmpeg_utils.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=sample_json, returncode=0)
        duration = ffmpeg_utils.get_duration("video.mp4")
    assert duration == 15.23


def test_extract_frames_builds_correct_commands():
    with patch("src.ffmpeg_utils.subprocess.run") as mock_run, \
         patch("src.ffmpeg_utils.Path.mkdir"):
        mock_run.return_value = MagicMock(returncode=0)
        paths = ffmpeg_utils.extract_frames("video.mp4", [0.0, 2.5], "frames/")
    assert len(paths) == 2
    assert paths[0].endswith("frame_000000.jpg")
    assert paths[1].endswith("frame_002500.jpg")


def test_get_video_dimensions_parses_json():
    sample_json = '{"streams": [{"width": "1080", "height": "1920"}]}'
    with patch("src.ffmpeg_utils.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=sample_json, returncode=0)
        w, h = ffmpeg_utils.get_video_dimensions("video.mp4")
    assert (w, h) == (1080, 1920)

