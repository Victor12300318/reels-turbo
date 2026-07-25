import json
import shutil
import subprocess
from pathlib import Path


def _ffprobe_path() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def _ffmpeg_path() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def get_duration(video_path: str) -> float:
    result = subprocess.run(
        [
            _ffprobe_path(),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def get_video_dimensions(video_path: str) -> tuple[int, int]:
    result = subprocess.run(
        [
            _ffprobe_path(),
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def extract_frames(video_path: str, timestamps: list[float], output_dir: str) -> list[str]:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    base = Path(video_path).stem
    for ts in timestamps:
        ms = int(ts * 1000)
        filename = out_path / f"{base}_frame_{ms:06d}.jpg"
        subprocess.run(
            [
                _ffmpeg_path(),
                "-y",
                "-ss", str(ts),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                str(filename),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        generated.append(str(filename))
    return generated


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run([_ffmpeg_path(), *args], check=True)


def calculate_frame_timestamps(duration: float, n: int) -> list[float]:
    if n <= 1:
        return [0.0]
    step = duration / (n + 1)
    return [step * i for i in range(1, n + 1)]
