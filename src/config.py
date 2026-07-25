import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash"
    local_videos_dir: str = r"C:\Users\victor.felix\Pictures\reels-turbo\Videos-fuga-novo"
    data_dir: str = "./data"
    frames_per_video: int = 3
    log_level: str = "INFO"
    evolution_api_base_url: str = "https://n8n-evolution-api.xjbony.easypanel.host/"
    evolution_api_instance: str = "Insta-clone"
    evolution_api_token: str = "75A575E588EB-4A32-9AEA-F717B8776D6C"
    whatsapp_test_number: str = "5511989238431"
    n8n_webhook_url: str = "https://n8n-n8n.xjbony.easypanel.host/webhook/4418ba5a-ab7a-4cf4-9dc6-b2da286fe337"
    instagram_cookies_file: str | None = None
    database_url: str = ""
    s3_access_key: str = "aFK6HG8Urf82JJ5pVkKo"
    s3_secret_key: str = "uip2cWiVVnMjaDK5KSFRuXs20BpQTjwJtw6eoBJz"
    s3_bucket: str = "reels-turbo"
    s3_endpoint: str = "crm-minio.xjbony.easypanel.host"
    s3_port: int = 443
    s3_ssl: bool = True
    s3_region: str = "us-east-1"
    s3_public_custom_domain: str = "https://crm-minio.xjbony.easypanel.host/reels-turbo"
    meta_app_id: str = "1337818285188918"
    meta_app_secret: str = "f2c34c8ff15ef22eccb7830cde268484"
    instagram_account_id: str = ""
    instagram_access_token: str = ""
    webhook_verify_token: str = "reels_cloner_token_123"


def get_settings() -> Settings:
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
        evolution_api_base_url=os.getenv("EVOLUTION_API_BASE_URL", "https://n8n-evolution-api.xjbony.easypanel.host/"),
        evolution_api_instance=os.getenv("EVOLUTION_API_INSTANCE", "Insta-clone"),
        evolution_api_token=os.getenv("EVOLUTION_API_TOKEN", "75A575E588EB-4A32-9AEA-F717B8776D6C"),
        whatsapp_test_number=os.getenv("WHATSAPP_TEST_NUMBER", "5511989238431"),
        n8n_webhook_url=os.getenv("N8N_WEBHOOK_URL", "https://n8n-n8n.xjbony.easypanel.host/webhook/4418ba5a-ab7a-4cf4-9dc6-b2da286fe337"),
        instagram_cookies_file=cookies_file,
        database_url=os.getenv("DATABASE_URL", ""),
        s3_access_key=os.getenv("S3_ACCESS_KEY", "aFK6HG8Urf82JJ5pVkKo"),
        s3_secret_key=os.getenv("S3_SECRET_KEY", "uip2cWiVVnMjaDK5KSFRuXs20BpQTjwJtw6eoBJz"),
        s3_bucket=os.getenv("S3_BUCKET", "reels-turbo"),
        s3_endpoint=os.getenv("S3_ENDPOINT", "crm-minio.xjbony.easypanel.host"),
        s3_port=int(os.getenv("S3_PORT", "443")),
        s3_ssl=os.getenv("S3_SSL", "true").lower() in ("true", "1", "yes"),
        s3_region=os.getenv("S3_REGION", "us-east-1"),
        s3_public_custom_domain=os.getenv("S3_PUBLIC_CUSTOM_DOMAIN", "https://crm-minio.xjbony.easypanel.host/reels-turbo"),
        meta_app_id=os.getenv("META_APP_ID", "1337818285188918"),
        meta_app_secret=os.getenv("META_APP_SECRET", "f2c34c8ff15ef22eccb7830cde268484"),
        instagram_account_id=os.getenv("INSTAGRAM_ACCOUNT_ID", ""),
        instagram_access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
        webhook_verify_token=os.getenv("WEBHOOK_VERIFY_TOKEN", "reels_cloner_token_123"),
    )
