import pytest
from unittest.mock import patch, MagicMock
from src.s3_client import S3Storage


@patch("src.s3_client.boto3.client")
def test_s3_upload(mock_boto_client, tmp_path):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(b"dummy video")

    s3 = S3Storage()
    url = s3.upload_file(str(test_file), object_name="user123/test.mp4")

    mock_s3.upload_file.assert_called_once()
    assert "user123/test.mp4" in url
