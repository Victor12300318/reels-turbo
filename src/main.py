import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.database import VideoRepository
from src.ai_client import get_ai_client
from src.analyzer import VideoAnalyzer
from src.indexer import index_videos_folder
from src.downloader import download_reels
from src.matcher import Matcher
from src.video_processor import VideoProcessor


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def index_command(args: argparse.Namespace):
    settings = get_settings()
    setup_logging(settings.log_level)
    db_location = settings.database_url if settings.database_url else str(Path(settings.data_dir) / "videos.db")
    repo = VideoRepository(db_location)
    repo.ensure_schema()
    client = get_ai_client(repo)
    analyzer = VideoAnalyzer(client)
    count = index_videos_folder(
        settings.local_videos_dir,
        analyzer,
        repo,
        frames_per_video=settings.frames_per_video,
        frames_output_dir=str(Path(settings.data_dir) / "frames"),
    )
    print(f"Indexed {count} videos from {settings.local_videos_dir}")


def clone_reels_pipeline(url: str, output_dir: str | None = None, user_id: str | None = None, job_id: str | None = None, progress_callback: Any = None) -> tuple[str, str]:
    settings = get_settings()
    db_location = settings.database_url if settings.database_url else str(Path(settings.data_dir) / "videos.db")
    repo = VideoRepository(db_location)
    repo.ensure_schema()
    candidates = repo.get_all(user_id=user_id)
    if not candidates and user_id:
        candidates = repo.get_all()
    if not candidates:
        raise ValueError("No local videos indexed. Upload local videos first.")

    client = get_ai_client(repo)
    analyzer = VideoAnalyzer(client)

    if progress_callback:
        progress_callback(15, "Baixando vídeo original do Instagram...")

    logging.info(f"Downloading reference Reels from {url}...")
    reference_path = download_reels(url, str(Path(settings.data_dir) / "downloads"))

    # Upload original downloaded reel to S3 so it can be previewed in frontend
    original_s3_url = ""
    try:
        from src.s3_client import S3Storage
        s3 = S3Storage()
        orig_key = f"originals/{user_id or 'admin'}/{Path(reference_path).name}"
        original_s3_url = s3.upload_file(reference_path, object_name=orig_key)
        if job_id:
            repo.update_job_original_url(job_id, original_s3_url)
    except Exception as s3_err:
        logging.warning(f"Failed to upload original video to S3: {s3_err}")

    if progress_callback:
        progress_callback(35, "Analisando elementos visuais e texto com IA...")

    logging.info("Analyzing reference video...")
    from src import ffmpeg_utils
    from PIL import Image

    ref_duration = ffmpeg_utils.get_duration(reference_path)
    ref_timestamps = ffmpeg_utils.calculate_frame_timestamps(ref_duration, settings.frames_per_video)
    ref_frame_paths = ffmpeg_utils.extract_frames(reference_path, ref_timestamps, str(Path(settings.data_dir) / "frames"))
    ref_frames = [Image.open(p) for p in ref_frame_paths]

    ref_description = analyzer.describe(ref_frames)
    on_screen_text = analyzer.extract_text(ref_frames)
    if not on_screen_text or not on_screen_text.strip():
        logging.info("Nenhum texto na tela extraído via OCR. Gerando headline de engajamento com a IA...")
        on_screen_text = analyzer.generate_headline_fallback(ref_frames, ref_description.get("description", ""))

    text_style = analyzer.analyze_text_style(ref_frames)

    if progress_callback:
        progress_callback(60, "Buscando melhor vídeo correspondente na biblioteca...")

    logging.info("Matching local videos...")
    matcher = Matcher(client)
    ranked = matcher.rank_candidates(ref_description["description"], candidates)
    if not ranked:
        raise ValueError("No suitable local video found.")

    winner = matcher.select_best_video(ref_frames, ranked[:3])
    logging.info(f"Selected local video: {winner['path']}")

    if progress_callback:
        progress_callback(80, "Renderizando vídeo final com áudio e overlay...")

    processor = VideoProcessor()
    audio_path = processor.extract_audio(reference_path, str(Path(settings.data_dir) / "audio.aac"))
    adjusted_path = processor.adjust_duration(
        winner["path"],
        ref_duration,
        str(Path(settings.data_dir) / "adjusted.mp4"),
    )

    frame_paths_list = winner.get("frame_paths") or []
    if not frame_paths_list:
        try:
            winner_dur = ffmpeg_utils.get_duration(winner["path"])
            frame_paths_list = ffmpeg_utils.extract_frames(winner["path"], [max(winner_dur / 2.0, 0.1)], str(Path(settings.data_dir) / "frames"))
        except Exception as ef:
            logging.warning(f"Could not extract fallback frame for winner video: {ef}")

    if frame_paths_list:
        middle_frame = Image.open(frame_paths_list[len(frame_paths_list) // 2])
        try:
            face_position = analyzer.detect_face_position(middle_frame)
        finally:
            middle_frame.close()
    else:
        face_position = "bottom"

    output_name = f"{Path(reference_path).stem}_final.mp4"
    output_path = Path(output_dir or Path(settings.data_dir) / "output") / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_path = processor.render_final_video(
        adjusted_path,
        audio_path,
        on_screen_text or "",
        face_position,
        str(output_path),
        text_style=text_style,
    )
    logging.info(f"Done: {final_path}")
    return final_path, original_s3_url


def clone_command(args: argparse.Namespace):
    settings = get_settings()
    setup_logging(settings.log_level)
    try:
        clone_reels_pipeline(args.url, args.output_dir)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Clonify AI CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index local videos")
    index_parser.set_defaults(func=index_command)

    clone_parser = subparsers.add_parser("clone", help="Clone a Reels using a local video")
    clone_parser.add_argument("url", help="Instagram Reels URL")
    clone_parser.add_argument("--output-dir", help="Directory for final video")
    clone_parser.set_defaults(func=clone_command)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
