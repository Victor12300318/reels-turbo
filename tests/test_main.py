from unittest.mock import patch, MagicMock
from src import main


def test_cli_index_parses():
    with patch("src.main.index_command") as mock_index:
        main.main(["index"])
    mock_index.assert_called_once()


def test_cli_clone_parses():
    with patch("src.main.clone_command") as mock_clone:
        main.main(["clone", "https://instagram.com/reel/abc"])
    mock_clone.assert_called_once()
    args, _ = mock_clone.call_args
    assert args[0].url == "https://instagram.com/reel/abc"
