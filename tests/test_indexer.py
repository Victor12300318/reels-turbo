from pathlib import Path
from unittest.mock import MagicMock, patch
from src.indexer import index_videos_folder


@patch("src.indexer.open_image")
@patch("src.indexer.ffmpeg_utils.extract_frames", return_value=["frame1.jpg", "frame2.jpg", "frame3.jpg"])
@patch("src.indexer.ffmpeg_utils.get_duration", return_value=10.0)
def test_index_videos_folder(mock_duration, mock_extract, mock_open, tmp_path):
    video = tmp_path / "sample.MP4"
    video.write_text("dummy")

    analyzer = MagicMock()
    analyzer.describe.return_value = {
        "description": "Test video",
        "themes": "test",
        "orientation": "portrait",
        "has_face": 1,
    }

    repo = MagicMock()
    repo.upsert = MagicMock()

    count = index_videos_folder(str(tmp_path), analyzer, repo)
    assert count == 1
    repo.upsert.assert_called_once()
    call_args = repo.upsert.call_args[0][0]
    assert call_args["filename"] == "sample.MP4"
    assert call_args["duration_seconds"] == 10.0
