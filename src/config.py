import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv, find_dotenv


def _load_env():
    dotenv_file = find_dotenv()
    if dotenv_file:
        override_env = "PYTEST_CURRENT_TEST" not in os.environ
        load_dotenv(dotenv_file, override=override_env)


_load_env()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash"
    local_videos_dir: str = r"C:\Users\victor.felix\Pictures\reels-turbo\Videos-fuga-novo"
    data_dir: str = "./data"
    frames_per_video: int = 3
    log_level: str = "INFO"
    evolution_api_base_url: str = ""
    evolution_api_instance: str = ""
    evolution_api_token: str = ""
    whatsapp_test_number: str = ""
    n8n_webhook_url: str = ""
    instagram_cookies_file: str | None = None
    database_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "reels-turbo"
    s3_endpoint: str = "crm-minio.xjbony.easypanel.host"
    s3_port: int = 443
    s3_ssl: bool = True
    s3_region: str = "us-east-1"
    s3_public_custom_domain: str = "https://crm-minio.xjbony.easypanel.host/reels-turbo"
    meta_app_id: str = "913982567729553"
    meta_app_secret: str = ""
    instagram_account_id: str = ""
    instagram_access_token: str = ""
    webhook_verify_token: str = "reels_cloner_token_123"
    admin_email: str = ""
    admin_password: str = ""
    jwt_secret: str = "reels_cloner_jwt_secret_change_me"


def get_settings() -> Settings:
    _load_env()
    cookies_file = os.getenv("INSTAGRAM_COOKIES_FILE")
    if not cookies_file:
        possible_paths = ["data/cookies.txt", "/app/data/cookies.txt", "./data/cookies.txt"]
        for p in possible_paths:
            if Path(p).exists():
                cookies_file = p
                break

    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        local_videos_dir=os.getenv(
            "LOCAL_VIDEOS_DIR",
            r"C:\Users\victor.felix\Pictures\reels-turbo\Videos-fuga-novo",
        ),
        data_dir=os.getenv("DATA_DIR", "./data"),
        frames_per_video=int(os.getenv("FRAMES_PER_VIDEO", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        evolution_api_base_url=os.getenv("EVOLUTION_API_BASE_URL", ""),
        evolution_api_instance=os.getenv("EVOLUTION_API_INSTANCE", ""),
        evolution_api_token=os.getenv("EVOLUTION_API_TOKEN", ""),
        whatsapp_test_number=os.getenv("WHATSAPP_TEST_NUMBER", ""),
        n8n_webhook_url=os.getenv("N8N_WEBHOOK_URL", ""),
        instagram_cookies_file=cookies_file,
        database_url=os.getenv("DATABASE_URL", ""),
        s3_access_key=os.getenv("S3_ACCESS_KEY", ""),
        s3_secret_key=os.getenv("S3_SECRET_KEY", ""),
        s3_bucket=os.getenv("S3_BUCKET", "reels-turbo"),
        s3_endpoint=os.getenv("S3_ENDPOINT", "crm-minio.xjbony.easypanel.host"),
        s3_port=int(os.getenv("S3_PORT", "443")),
        s3_ssl=os.getenv("S3_SSL", "true").lower() in ("true", "1", "yes"),
        s3_region=os.getenv("S3_REGION", "us-east-1"),
        s3_public_custom_domain=os.getenv("S3_PUBLIC_CUSTOM_DOMAIN", "https://crm-minio.xjbony.easypanel.host/reels-turbo"),
        meta_app_id=os.getenv("META_APP_ID", "913982567729553"),
        meta_app_secret=os.getenv("META_APP_SECRET", ""),
        instagram_account_id=os.getenv("INSTAGRAM_ACCOUNT_ID", ""),
        instagram_access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
        webhook_verify_token=os.getenv("WEBHOOK_VERIFY_TOKEN", "reels_cloner_token_123"),
        admin_email=os.getenv("ADMIN_EMAIL", ""),
        admin_password=os.getenv("ADMIN_PASSWORD", ""),
        jwt_secret=os.getenv("JWT_SECRET", "reels_cloner_jwt_secret_change_me"),
    )
