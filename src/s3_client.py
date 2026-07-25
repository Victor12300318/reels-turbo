import logging
from pathlib import Path
import boto3
from botocore.config import Config
from src.config import get_settings

logger = logging.getLogger(__name__)


class S3Storage:
    def __init__(self):
        self.settings = get_settings()
        endpoint_scheme = "https" if self.settings.s3_ssl else "http"
        endpoint_url = f"{endpoint_scheme}://{self.settings.s3_endpoint}"
        if self.settings.s3_port and self.settings.s3_port not in (80, 443):
            endpoint_url += f":{self.settings.s3_port}"

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            region_name=self.settings.s3_region,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = self.settings.s3_bucket

    def upload_file(self, local_path: str, object_name: str | None = None) -> str:
        """
        Uploads a local file to S3/MinIO and returns the public access URL.
        """
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found for S3 upload: {local_path}")

        key = object_name or path.name
        content_type = "video/mp4" if path.suffix.lower() == ".mp4" else "application/octet-stream"

        try:
            logger.info(f"Uploading '{local_path}' to S3 bucket '{self.bucket}' as '{key}'...")
            self.client.upload_file(
                str(path),
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type}
            )

            public_domain = self.settings.s3_public_custom_domain.rstrip("/")
            public_url = f"{public_domain}/{key}"
            logger.info(f"Upload complete. Public URL: {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise
