import pytest
from unittest.mock import patch, MagicMock
from src.instagram_publisher import InstagramPublisher


@patch("src.instagram_publisher.httpx.post")
@patch("src.instagram_publisher.httpx.get")
def test_publish_reel_flow(mock_get, mock_post):
    # Mock Container creation response
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"id": "container_123"}),  # step 1: create
        MagicMock(status_code=200, json=lambda: {"id": "media_999"}),      # step 3: publish
    ]
    # Mock Container status check
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})

    publisher = InstagramPublisher()
    result = publisher.publish_reel(
        video_url="https://crm-minio.xjbony.easypanel.host/typebot/sample.mp4",
        caption="Legenda do Reels",
        instagram_account_id="17841400000000000",
        access_token="EAAG..."
    )

    assert result["id"] == "media_999"
    assert mock_post.call_count == 2
    mock_get.assert_called_once()


@patch("src.instagram_publisher.httpx.post")
@patch("src.instagram_publisher.httpx.get")
def test_publish_reel_share_to_feed_false(mock_get, mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"id": "container_123"}),
        MagicMock(status_code=200, json=lambda: {"id": "media_999"}),
    ]
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})

    publisher = InstagramPublisher()
    result = publisher.publish_reel(
        video_url="https://crm-minio.xjbony.easypanel.host/reels-turbo/sample.mp4",
        caption="Test Reels Only",
        instagram_account_id="17841400000000000",
        access_token="EAAG...",
        share_to_feed=False
    )

    assert result["id"] == "media_999"
    first_post_data = mock_post.call_args_list[0][1]["data"]
    assert first_post_data.get("share_to_feed") == "false"
