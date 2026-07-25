import os
import logging
import base64
import hashlib
import secrets
import shutil
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, RedirectResponse
from src.main import clone_reels_pipeline
from src.config import get_settings
from src.database import VideoRepository
from src.gemini_client import GeminiClient
from src.analyzer import VideoAnalyzer
from src.indexer import index_videos_folder

import asyncio

app = FastAPI(
    title="Reels Cloner API",
    description="API webhook e plataforma para clonagem de Reels com suporte a Atalho do iPhone e Dashboard Next.js",
    version="2.0.0",
)

@app.on_event("startup")
async def start_background_scheduler():
    async def scheduler_loop():
        while True:
            try:
                repo = get_repo()
                from src.scheduler import process_due_scheduled_jobs
                process_due_scheduled_jobs(repo)
            except Exception as e:
                logging.error(f"Error in background scheduler loop: {e}")
            await asyncio.sleep(60)

    asyncio.create_task(scheduler_loop())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def get_repo() -> VideoRepository:
    db_loc = settings.database_url if settings.database_url else str(Path(settings.data_dir) / "videos.db")
    try:
        repo = VideoRepository(db_loc)
        repo.ensure_schema()
        return repo
    except Exception as e:
        if settings.database_url:
            logging.warning(f"Could not connect to PostgreSQL ({e}), falling back to local SQLite database.")
            fallback_loc = str(Path(settings.data_dir) / "videos.db")
            repo = VideoRepository(fallback_loc)
            repo.ensure_schema()
            return repo
        raise


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_or_create_default_user(repo: VideoRepository) -> dict:
    admin = repo.get_user_by_email("admin@reels.com")
    if not admin:
        admin = repo.create_user(
            email="admin@reels.com",
            password_hash=hash_password("admin123"),
            api_key="usr_admin_default_key"
        )
    return admin


def authenticate_request(request: Request, x_api_key: str | None = None) -> dict:
    repo = get_repo()

    # 1. Check X-API-Key / apikey header
    api_key = x_api_key or request.headers.get("x-api-key") or request.headers.get("apikey")
    
    # 2. Check Authorization header
    auth_header = request.headers.get("authorization", "")
    if not api_key and auth_header.startswith("Bearer "):
        api_key = auth_header.split(" ", 1)[1]

    # 3. Check query param
    if not api_key:
        api_key = request.query_params.get("api_key")

    if api_key:
        user = repo.get_user_by_api_key(api_key)
        if user:
            return user

    # Default fallback to default admin
    return get_or_create_default_user(repo)


def background_job_processor(job_id: str, user_id: str, url: str, output_dir: str | None, webhook_url: str | None) -> None:
    repo = get_repo()
    repo.update_job(job_id, status="processing", progress=5)

    def on_progress(percent: int, status_msg: str):
        repo.update_job(job_id, status="processing", progress=percent)

    try:
        logging.info(f"[Job {job_id}] Starting clone for user {user_id}: {url}")
        res = clone_reels_pipeline(url, output_dir=output_dir, user_id=user_id, job_id=job_id, progress_callback=on_progress)
        final_video_path = res[0] if isinstance(res, tuple) else res
        
        # Try uploading rendered AI video to S3
        on_progress(90, "Enviando vídeo para nuvem S3...")
        public_url = final_video_path
        try:
            from src.s3_client import S3Storage
            s3 = S3Storage()
            s3_key = f"jobs/{user_id}/{job_id}_{os.path.basename(final_video_path)}"
            public_url = s3.upload_file(final_video_path, object_name=s3_key)
        except Exception as s3_err:
            logging.warning(f"S3 upload failed, keeping local path: {s3_err}")

        repo.update_job(job_id, status="completed", progress=100, output_path=public_url)
        logging.info(f"[Job {job_id}] Completed successfully: {public_url}")

        # Auto-post to Instagram if credentials are set
        user = repo.get_user_by_id(user_id) or {}
        ig_account_id = user.get("instagram_account_id") or settings.instagram_account_id
        ig_token = user.get("instagram_access_token") or settings.instagram_access_token
        if ig_account_id and ig_token and public_url.startswith("http"):
            try:
                from src.instagram_publisher import InstagramPublisher
                logging.info(f"[Job {job_id}] Auto-posting Reels to Instagram account {ig_account_id}...")
                publisher = InstagramPublisher()
                publisher.publish_reel(
                    video_url=public_url,
                    caption="Clonado com Reels Cloner AI #reels",
                    instagram_account_id=ig_account_id,
                    access_token=ig_token
                )
            except Exception as ig_err:
                logging.error(f"[Job {job_id}] Instagram auto-post failed: {ig_err}")

        if webhook_url:
            send_video_to_n8n(final_video_path, url, webhook_url)
    except Exception as e:
        error_msg = str(e)
        logging.error(f"[Job {job_id}] Failed: {error_msg}")
        repo.update_job(job_id, status="failed", error=error_msg)


def background_clone_and_send(url: str, output_dir: str | None = None, webhook_url: str | None = None, job_id: str | None = None, user_id: str | None = None) -> None:
    if job_id and user_id:
        background_job_processor(job_id, user_id, url, output_dir, webhook_url)
    else:
        try:
            res = clone_reels_pipeline(url, output_dir=output_dir, user_id=user_id)
            final_video_path = res[0] if isinstance(res, tuple) else res
            if webhook_url:
                send_video_to_n8n(final_video_path, url, webhook_url)
        except Exception as e:
            logging.error(f"Erro na clonagem: {e}")


def send_video_to_n8n(video_path: str, original_url: str, webhook_url: str) -> None:
    if not webhook_url:
        return
    try:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Arquivo de vídeo não encontrado em: {video_path}")
        with open(video_path, "rb") as f:
            video_bytes = f.read()
            video_base64 = base64.b64encode(video_bytes).decode("utf-8")
        payload = {
            "status": "success",
            "url": original_url,
            "file_name": os.path.basename(video_path),
            "video_base64": video_base64
        }
        httpx.post(webhook_url, json=payload, timeout=120.0)
    except Exception as e:
        logging.error(f"Erro ao enviar vídeo para n8n: {e}")
        try:
            fail_payload = {
                "status": "failed",
                "url": original_url,
                "error": str(e)
            }
            httpx.post(webhook_url, json=fail_payload, timeout=30.0)
        except Exception as send_err:
            logging.error(f"Falha ao enviar notificação de erro para o n8n: {str(send_err)}")


# --- AUTH & USER ENDPOINTS ---

@app.post("/api/v1/auth/login")
async def login(request: Request):
    body = await request.json()
    email = body.get("email", "").strip()
    password = body.get("password", "").strip()

    repo = get_repo()
    user = repo.get_user_by_email(email)
    
    # Auto-seed default user if database is completely empty
    if not user and email == "admin@reels.com":
        user = get_or_create_default_user(repo)

    if not user or user["password_hash"] != hash_password(password):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    return {
        "user_id": user["id"],
        "email": user["email"],
        "api_key": user["api_key"]
    }


@app.get("/api/v1/user/me")
def get_me(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    return {
        "id": user["id"],
        "email": user["email"],
        "api_key": user["api_key"],
        "instagram_account_id": user.get("instagram_account_id") or "",
        "instagram_access_token": user.get("instagram_access_token") or "",
        "default_caption_suffix": user.get("default_caption_suffix") or "",
        "share_to_feed": user.get("share_to_feed", 0),
        "default_post_interval_hours": user.get("default_post_interval_hours", 3)
    }


@app.post("/api/v1/user/settings")
async def update_user_settings_endpoint(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    body = await request.json()
    default_caption_suffix = body.get("default_caption_suffix", "").strip()
    share_to_feed = 1 if body.get("share_to_feed") in (True, 1, "true", "1") else 0
    default_post_interval_hours = int(body.get("default_post_interval_hours", 3))

    repo = get_repo()
    repo.update_user_settings(user["id"], default_caption_suffix, share_to_feed, default_post_interval_hours)

    return {
        "status": "success",
        "message": "Configurações salvas com sucesso!",
        "default_caption_suffix": default_caption_suffix,
        "share_to_feed": share_to_feed,
        "default_post_interval_hours": default_post_interval_hours
    }


@app.post("/api/v1/user/instagram")
async def update_instagram_credentials(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    body = await request.json()
    account_id = body.get("instagram_account_id", "").strip()
    token = body.get("instagram_access_token", "").strip()

    repo = get_repo()
    repo.update_user_instagram_credentials(user["id"], account_id, token)

    return {
        "status": "success",
        "message": "Credenciais do Instagram salvas com sucesso!",
        "instagram_account_id": account_id
    }


# --- CLONE & JOBS ENDPOINTS ---

@app.post("/api/v1/clone")
@app.post("/api/clone")
async def clone_video(request: Request, background_tasks: BackgroundTasks, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()

    content_type = request.headers.get("content-type", "")
    url = None
    output_dir = None
    webhook_url = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            url = body.get("url")
            output_dir = body.get("output_dir")
            webhook_url = body.get("webhook_url")
        except Exception:
            pass

    if not url:
        try:
            form = await request.form()
            url = form.get("url")
            output_dir = form.get("output_dir")
            webhook_url = form.get("webhook_url")
        except Exception:
            pass

    if not url:
        raise HTTPException(status_code=400, detail="O parâmetro 'url' é obrigatório.")

    # Create job entry
    job = repo.create_job(user_id=user["id"], url=str(url))

    # Add background task
    target_webhook = webhook_url or settings.n8n_webhook_url
    background_tasks.add_task(
        background_clone_and_send,
        str(url),
        output_dir,
        target_webhook,
        job_id=job["id"],
        user_id=user["id"]
    )

    return {
        "status": "processing",
        "job_id": job["id"],
        "message": "A clonagem do Reels foi iniciada com sucesso em segundo plano!",
        "url": url,
        "webhook_target": target_webhook,
    }


@app.get("/api/v1/jobs")
def list_jobs(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()
    jobs = repo.get_jobs_by_user(user["id"])
    return {"jobs": jobs}


@app.get("/api/v1/jobs/calendar")
def get_jobs_calendar(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()
    jobs = repo.get_jobs_by_user(user["id"])
    return {"calendar": jobs}


@app.post("/api/v1/jobs/batch-schedule")
async def batch_schedule_jobs(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    body = await request.json()
    job_ids = body.get("job_ids", [])
    interval_hours = int(body.get("interval_hours", user.get("default_post_interval_hours", 3)))
    start_time = body.get("start_time")
    share_to_feed = 1 if body.get("share_to_feed") in (True, 1, "true", "1") else user.get("share_to_feed", 0)

    if not job_ids:
        raise HTTPException(status_code=400, detail="Nenhum job_id fornecido.")

    from src.scheduler import calculate_batch_timestamps
    timestamps = calculate_batch_timestamps(len(job_ids), start_time, interval_hours)

    repo = get_repo()
    updated_jobs = []

    for idx, jid in enumerate(job_ids):
        job = repo.get_job(jid)
        if not job or job["user_id"] != user["id"]:
            continue
        
        caption = job.get("caption") or ""
        if not caption and user.get("default_caption_suffix"):
            caption = user.get("default_caption_suffix")

        sched_time = timestamps[idx]
        repo.update_job_schedule(jid, caption=caption, scheduled_at=sched_time, share_to_feed=share_to_feed)
        updated_jobs.append({"id": jid, "scheduled_at": sched_time})

    return {
        "status": "success",
        "message": f"{len(updated_jobs)} vídeos agendados a cada {interval_hours} horas com sucesso!",
        "scheduled": updated_jobs
    }


@app.post("/api/v1/jobs/{job_id}/publish")
async def publish_job_now(job_id: str, request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    
    caption = body.get("caption")
    share_to_feed = body.get("share_to_feed")
    
    repo = get_repo()
    job = repo.get_job(job_id)
    if not job or job["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    if job["status"] != "completed" or not job.get("output_path"):
        raise HTTPException(status_code=400, detail="Vídeo ainda não foi renderizado ou falhou.")

    ig_account_id = user.get("instagram_account_id") or settings.instagram_account_id
    ig_token = user.get("instagram_access_token") or settings.instagram_access_token

    if not ig_account_id or not ig_token:
        raise HTTPException(status_code=400, detail="Conecte sua conta do Instagram no painel antes de publicar.")

    from src.instagram_publisher import InstagramPublisher
    publisher = InstagramPublisher()
    final_caption = caption or job.get("caption") or user.get("default_caption_suffix") or "Clonado com Reels Cloner AI #reels"
    stf = bool(share_to_feed if share_to_feed is not None else job.get("share_to_feed", user.get("share_to_feed", 0)))

    result = publisher.publish_reel(
        video_url=job["output_path"],
        caption=final_caption,
        instagram_account_id=ig_account_id,
        access_token=ig_token,
        share_to_feed=stf
    )

    repo.mark_job_posted(job_id)

    return {
        "status": "success",
        "message": "Reels publicado no Instagram com sucesso!",
        "media_id": result.get("id")
    }


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str, request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return job


@app.get("/api/v1/jobs/{job_id}/download")
def download_job_output(job_id: str, request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()
    job = repo.get_job(job_id)
    if not job or job["status"] != "completed" or not job["output_path"]:
        raise HTTPException(status_code=404, detail="Vídeo não pronto ou não encontrado.")
    
    file_path = job["output_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não existe mais no servidor.")
    
    return FileResponse(file_path, media_type="video/mp4", filename=os.path.basename(file_path))


# --- VIDEO LIBRARY ENDPOINTS ---

@app.post("/api/v1/videos/upload")
async def upload_video(
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None)
):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()

    upload_list = []
    try:
        form = await request.form()
        for key, value in form.items():
            if hasattr(value, "filename") and value.filename:
                upload_list.append(value)
    except Exception as e:
        logging.error(f"Error parsing form data: {e}")
        raise HTTPException(status_code=400, detail="Formato de upload inválido.")

    if not upload_list:
        raise HTTPException(status_code=400, detail="Nenhum arquivo de vídeo foi selecionado para upload.")

    user_video_dir = Path(settings.data_dir) / "users" / user["id"] / "videos"
    user_video_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for f in upload_list[:30]:  # Limit to 30 files per batch
        if not f.filename.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
            continue

        dest_path = user_video_dir / f.filename
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        saved_files.append(dest_path)

        # Upload library video to S3
        try:
            from src.s3_client import S3Storage
            s3 = S3Storage()
            s3_key = f"library/{user['id']}/{f.filename}"
            s3.upload_file(str(dest_path), object_name=s3_key)
        except Exception as s3_err:
            logging.warning(f"Failed to upload library video '{f.filename}' to S3: {s3_err}")

    # Enqueue background indexer for user directory
    def index_batch():
        try:
            client = GeminiClient(settings.gemini_api_key, settings.gemini_model)
            analyzer = VideoAnalyzer(client)
            index_videos_folder(
                str(user_video_dir),
                analyzer,
                repo,
                frames_per_video=settings.frames_per_video,
                frames_output_dir=str(Path(settings.data_dir) / "frames"),
            )
            for path_obj in saved_files:
                video_rec = repo.get_by_path(str(path_obj))
                if video_rec:
                    repo.upsert(video_rec, user_id=user["id"])
        except Exception as e:
            logging.error(f"Erro ao indexar lote de vídeos: {e}")

    background_tasks.add_task(index_batch)

    return {
        "status": "uploaded",
        "message": f"{len(saved_files)} vídeo(s) enviado(s) com sucesso e enfileirado(s) para indexação!",
        "count": len(saved_files),
    }


# --- ADMIN INSTAGRAM COOKIES ENDPOINTS ---

@app.post("/api/v1/admin/cookies")
async def upload_cookies(
    request: Request,
    x_api_key: str | None = Header(None)
):
    user = authenticate_request(request, x_api_key)
    cookie_path = Path(settings.data_dir) / "cookies.txt"
    cookie_path.parent.mkdir(parents=True, exist_ok=True)

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        cookie_file = form.get("file")
        if not cookie_file or not hasattr(cookie_file, "file"):
            raise HTTPException(status_code=400, detail="Arquivo cookies.txt não enviado.")
        
        with open(cookie_path, "wb") as f:
            shutil.copyfileobj(cookie_file.file, f)
    else:
        body = await request.json()
        cookies_text = body.get("cookies_text", "").strip()
        if not cookies_text:
            raise HTTPException(status_code=400, detail="Conteúdo do cookie em texto está vazio.")
        
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(cookies_text)

    return {
        "status": "success",
        "message": "Arquivo cookies.txt do Instagram salvo e ativado com sucesso para o yt-dlp!"
    }


@app.get("/api/v1/admin/cookies/status")
def get_cookies_status(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    cookie_path = Path(settings.data_dir) / "cookies.txt"

    if cookie_path.exists() and cookie_path.stat().st_size > 0:
        return {
            "status": "active",
            "size_bytes": cookie_path.stat().st_size,
            "message": "cookies.txt está ativo e pronto para downloads do Instagram."
        }
    return {
        "status": "missing",
        "message": "cookies.txt não configurado. Reels privados ou protegidos podem falhar no download."
    }


@app.get("/api/v1/videos")
def list_videos(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()
    videos = repo.get_all(user_id=user["id"])
    return {"videos": videos}


@app.delete("/api/v1/videos/{video_id}")
def delete_video_endpoint(video_id: int, request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()
    repo.delete_video(video_id, user["id"])
    return {"status": "success", "message": "Vídeo removido com sucesso."}


@app.get("/api/v1/metrics")
def get_metrics(request: Request, x_api_key: str | None = Header(None)):
    user = authenticate_request(request, x_api_key)
    repo = get_repo()
    jobs = repo.get_jobs_by_user(user["id"])
    videos = repo.get_all(user_id=user["id"])

    total_cloned = len([j for j in jobs if j.get("status") in ("completed", "scheduled")])
    total_published = len([j for j in jobs if j.get("posted_at") or j.get("status") == "completed"])
    scheduled_count = len([j for j in jobs if j.get("status") == "scheduled"])

    return {
        "total_cloned": total_cloned,
        "total_published": total_published,
        "library_count": len(videos),
        "scheduled_count": scheduled_count
    }


# --- META WEBHOOK & OAUTH ENDPOINTS ---

@app.get("/api/v1/webhook/instagram")
@app.get("/webhook/instagram")
@app.get("/webhook")
def verify_meta_webhook(request: Request):
    """
    Endpoint for Meta Developers Webhook Verification.
    Reads hub.mode, hub.challenge, hub.verify_token from query params.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    logging.info(f"Meta Webhook verification request: mode={mode}, token={token}, challenge={challenge}")

    if mode == "subscribe" and challenge:
        return Response(content=challenge, media_type="text/plain", status_code=200)

    if challenge:
        return Response(content=challenge, media_type="text/plain", status_code=200)

    return {"status": "ok", "message": "Meta Webhook Endpoint active"}


@app.post("/api/v1/webhook/instagram")
@app.post("/webhook/instagram")
@app.post("/webhook")
async def handle_meta_webhook(request: Request):
    try:
        body = await request.json()
        logging.info(f"Received Meta Webhook event: {body}")
    except Exception:
        pass
    return {"status": "EVENT_RECEIVED"}


@app.get("/api/v1/auth/instagram/login")
def instagram_login(redirect_uri: str = "https://4319-170-254-145-205.ngrok-free.app/api/v1/auth/instagram/callback"):
    meta_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={settings.meta_app_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement&"
        f"response_type=code"
    )
    return RedirectResponse(url=meta_url)


@app.get("/api/v1/auth/instagram/callback")
async def instagram_callback(
    code: str = "",
    error: str = "",
    redirect_uri: str = "https://4319-170-254-145-205.ngrok-free.app/api/v1/auth/instagram/callback"
):
    if error or not code:
        return RedirectResponse(url="/?error=instagram_login_failed")

    try:
        token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
        res = httpx.get(token_url, params={
            "client_id": settings.meta_app_id,
            "client_secret": settings.meta_app_secret,
            "redirect_uri": redirect_uri,
            "code": code
        }, timeout=30.0)
        token_data = res.json()
        short_token = token_data.get("access_token")

        if not short_token:
            return RedirectResponse(url="/?error=invalid_token")

        # Exchange for Long-Lived Access Token
        long_token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
        res_long = httpx.get(long_token_url, params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.meta_app_id,
            "client_secret": settings.meta_app_secret,
            "fb_exchange_token": short_token
        }, timeout=30.0)
        long_token_data = res_long.json()
        long_token = long_token_data.get("access_token", short_token)

        # Get connected Instagram Account ID
        me_url = f"https://graph.facebook.com/v19.0/me/accounts?fields=instagram_business_account&access_token={long_token}"
        me_res = httpx.get(me_url, timeout=30.0)
        me_data = me_res.json()

        ig_account_id = ""
        for page in me_data.get("data", []):
            if "instagram_business_account" in page:
                ig_account_id = page["instagram_business_account"]["id"]
                break

        if not ig_account_id:
            try:
                direct_me = httpx.get(f"https://graph.facebook.com/v19.0/me?fields=id&access_token={long_token}", timeout=30.0).json()
                ig_account_id = str(direct_me.get("id", ""))
            except Exception:
                pass

        repo = get_repo()
        admin = get_or_create_default_user(repo)
        repo.update_user_instagram_credentials(admin["id"], ig_account_id or "connected", long_token)

        return RedirectResponse(url="/?status=instagram_connected")
    except Exception as e:
        logging.error(f"Error in Instagram OAuth callback: {e}")
        return RedirectResponse(url="/?error=oauth_exception")


@app.get("/health")
def health_check():
    return {"status": "ok", "model": settings.gemini_model}

