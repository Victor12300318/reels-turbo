import time
import logging
import httpx
from src.config import get_settings

logger = logging.getLogger(__name__)


class InstagramPublisher:
    def __init__(self, api_version: str = "v19.0"):
        self.settings = get_settings()
        self.api_version = api_version

    def _get_base_urls(self, access_token: str) -> list[str]:
        if access_token.startswith("IG"):
            return [
                f"https://graph.instagram.com/{self.api_version}",
                f"https://graph.facebook.com/{self.api_version}",
            ]
        return [
            f"https://graph.facebook.com/{self.api_version}",
            f"https://graph.instagram.com/{self.api_version}",
        ]

    def publish_reel(
        self,
        video_url: str,
        caption: str = "",
        instagram_account_id: str | None = None,
        access_token: str | None = None,
        share_to_feed: bool = False,
    ) -> dict:
        account_id = instagram_account_id or self.settings.instagram_account_id
        token = access_token or self.settings.instagram_access_token

        if not account_id or not token:
            raise ValueError("Instagram Account ID and Access Token are required for automatic posting.")

        if "@" in account_id:
            raise ValueError(f"O Instagram Account ID deve ser o ID numérico da conta do Meta Graph API (ex: 17841400000000000), e não o e-mail '{account_id}'.")

        logger.info(f"Step 1: Creating Instagram Reels container for URL: {video_url} (share_to_feed={share_to_feed})...")
        container_id, base_url = self._create_container(account_id, token, video_url, caption, share_to_feed=share_to_feed)

        logger.info(f"Step 2: Waiting for container {container_id} to finish processing...")
        self._wait_for_container(container_id, token, base_url)

        logger.info(f"Step 3: Publishing container {container_id} to Instagram account {account_id}...")
        result = self._publish_container(account_id, token, container_id, base_url)
        
        logger.info(f"Reels published successfully to Instagram! Media ID: {result.get('id')}")
        return result

    def _create_container(self, account_id: str, access_token: str, video_url: str, caption: str, share_to_feed: bool = False) -> tuple[str, str]:
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": access_token,
            "share_to_feed": "true" if share_to_feed else "false",
        }

        last_error = None
        for base_url in self._get_base_urls(access_token):
            url = f"{base_url}/{account_id}/media"
            try:
                res = httpx.post(url, data=payload, timeout=60.0)
                data = res.json()
                if res.status_code == 200 and "id" in data:
                    return data["id"], base_url
                last_error = data
            except Exception as e:
                last_error = str(e)

        raise RuntimeError(f"Failed to create Instagram Reels container: {last_error}")

    def _wait_for_container(self, container_id: str, access_token: str, base_url: str, timeout: int = 300) -> None:
        url = f"{base_url}/{container_id}"
        params = {"fields": "status_code,status", "access_token": access_token}
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            res = httpx.get(url, params=params, timeout=30.0)
            data = res.json()
            status_code = data.get("status_code")
            
            logger.info(f"Container {container_id} status: {status_code}")
            
            if status_code == "FINISHED":
                return
            elif status_code in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram processing failed for container {container_id}: {data}")
            
            time.sleep(5)
            
        raise TimeoutError(f"Container {container_id} processing timed out after {timeout} seconds.")

    def _publish_container(self, account_id: str, access_token: str, container_id: str, base_url: str) -> dict:
        url = f"{base_url}/{account_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": access_token,
        }
        res = httpx.post(url, data=payload, timeout=60.0)
        data = res.json()
        if res.status_code == 200 and "id" in data:
            return data
        raise RuntimeError(f"Failed to publish Instagram Reels container: {data}")

    def fetch_media_insights(self, media_id: str, access_token: str) -> dict:
        metrics = {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "reach": 0,
            "engagement_score": 0.0
        }
        if not media_id or not access_token:
            return metrics

        for base_url in self._get_base_urls(access_token):
            url = f"{base_url}/{media_id}/insights"
            params = {
                "metric": "plays,likes,comments,shares,reach",
                "access_token": access_token
            }
            try:
                res = httpx.get(url, params=params, timeout=30.0)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    for item in data:
                        name = item.get("name")
                        values = item.get("values", [])
                        val = values[0].get("value", 0) if values else 0
                        if name in ("plays", "views"):
                            metrics["views"] = int(val)
                        elif name == "likes":
                            metrics["likes"] = int(val)
                        elif name == "comments":
                            metrics["comments"] = int(val)
                        elif name == "shares":
                            metrics["shares"] = int(val)
                        elif name == "reach":
                            metrics["reach"] = int(val)

                    metrics["engagement_score"] = float(
                        metrics["views"] +
                        (metrics["likes"] * 3.0) +
                        (metrics["comments"] * 5.0) +
                        (metrics["shares"] * 7.0)
                    )
                    return metrics
            except Exception as e:
                logger.warning(f"Error fetching insights for media {media_id}: {e}")

        return metrics
        return data
