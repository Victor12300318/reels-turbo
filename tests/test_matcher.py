from unittest.mock import MagicMock
from src.matcher import Matcher


def test_rank_candidates():
    mock_client = MagicMock()
    # "b.mp4" is index 2, "a.mp4" is index 1
    mock_client.analyze.return_value = '{"ranking": [{"video_id": 2, "reason": "similar beach theme"}, {"video_id": 1, "reason": "city"}]}'
    matcher = Matcher(mock_client)
    candidates = [
        {"path": "a.mp4", "description": "City"},
        {"path": "b.mp4", "description": "Beach"},
    ]
    result = matcher.rank_candidates("Beach vibes", candidates)
    assert result[0]["path"] == "b.mp4"


def test_select_best_video():
    mock_client = MagicMock()
    # "b.mp4" is index 2
    mock_client.analyze.return_value = '{"best_video_id": 2, "reason": "colors match"}'
    matcher = Matcher(mock_client)
    from PIL import Image
    ref_frames = [Image.new("RGB", (10, 10))]
    top = [{"path": "a.mp4", "frame_paths": []}, {"path": "b.mp4", "frame_paths": []}]
    winner = matcher.select_best_video(ref_frames, top)
    assert winner["path"] == "b.mp4"
