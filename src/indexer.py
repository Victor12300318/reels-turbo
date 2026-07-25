from pathlib import Path
from src.analyzer import VideoAnalyzer
from src.database import VideoRepository
from src import ffmpeg_utils


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def _list_video_files(directory: str) -> list[Path]:
    path = Path(directory)
    if not path.exists():
        return []
    files = [p for p in path.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS]
    return sorted(files)


def index_videos_folder(
    videos_dir: str,
    analyzer: VideoAnalyzer,
    repo: VideoRepository,
    frames_per_video: int = 3,
    frames_output_dir: str = "./data/frames",
    user_id: str | None = None
) -> int:
    files = _list_video_files(videos_dir)
    indexed = 0
    for file_path in files:
        duration = 0.0
        try:
            duration = ffmpeg_utils.get_duration(str(file_path))
        except Exception:
            pass

        description = {}
        frame_paths = []
        try:
            timestamps = ffmpeg_utils.calculate_frame_timestamps(duration, frames_per_video)
            frame_paths = ffmpeg_utils.extract_frames(str(file_path), timestamps, frames_output_dir)

            images = [open_image(p) for p in frame_paths]
            try:
                description = analyzer.describe(images)
            finally:
                for img in images:
                    img.close()
        except Exception as e:
            import logging
            logging.warning(f"Não foi possível analisar vídeo '{file_path.name}' via Gemini: {e}")

        repo.upsert({
            "path": str(file_path),
            "filename": file_path.name,
            "description": description.get("description", "Vídeo local pronto para uso"),
            "themes": description.get("themes", ""),
            "orientation": description.get("orientation", "vertical"),
            "duration_seconds": duration,
            "has_face": int(description.get("has_face", 0)),
            "frame_paths": frame_paths,
        }, user_id=user_id)
        indexed += 1
    return indexed


def open_image(path: str):
    from PIL import Image
    return Image.open(path)
