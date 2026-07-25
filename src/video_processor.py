import math
import os
import re
from pathlib import Path
from src import ffmpeg_utils


SIZE_RATIOS = {
    "small": 0.04,
    "medium": 0.055,
    "large": 0.075,
    "xlarge": 0.095,
}


class VideoProcessor:
    def __init__(self, ffmpeg_path: str | None = None):
        self.ffmpeg_path = ffmpeg_path

    def extract_audio(self, video_path: str, output_audio_path: str) -> str:
        Path(output_audio_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_utils.run_ffmpeg([
            "-y",
            "-i", video_path,
            "-vn",
            "-c:a", "aac",
            "-b:a", "192k",
            output_audio_path,
        ])
        return output_audio_path

    def adjust_duration(self, video_path: str, target_duration: float, output_path: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        current_duration = ffmpeg_utils.get_duration(video_path)

        if current_duration < target_duration:
            loops = math.ceil(target_duration / current_duration)
            concat_list_path = str(Path(output_path).parent / "concat_list.txt")
            abs_video_path = str(Path(video_path).resolve())
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for _ in range(loops):
                    f.write(f"file '{abs_video_path.replace(chr(39), chr(39)+chr(39))}'\n")
            ffmpeg_utils.run_ffmpeg([
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                "-an",
                "-t", str(target_duration),
                output_path,
            ])
            os.remove(concat_list_path)
        else:
            ffmpeg_utils.run_ffmpeg([
                "-y",
                "-i", video_path,
                "-c", "copy",
                "-an",
                "-t", str(target_duration),
                output_path,
            ])
        return output_path

    def render_final_video(
        self,
        video_path: str,
        audio_path: str,
        text: str,
        face_position: str,
        output_path: str,
        text_style: dict | None = None,
        font_path: str = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        style = text_style or {}
        width, height = ffmpeg_utils.get_video_dimensions(video_path)
        filter_str = _build_drawtext_filter(
            text=text,
            style=style,
            face_position=face_position,
            video_width=width,
            video_height=height,
            font_path=font_path,
        )

        ffmpeg_utils.run_ffmpeg([
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ])
        return output_path


def _sanitize_text_for_ffmpeg(text: str) -> str:
    """
    Filtra caracteres que o FFmpeg não consegue renderizar com a fonte padrão,
    como emojis e símbolos especiais exóticos, evitando quadrados brancos [] na tela.
    """
    # Regex que remove emojis e caracteres fora do escopo padrão de texto latino + acentuação portuguesa
    # Mantém letras, números, acentuação padrão, pontuação comum e quebra de linhas.
    allowed_pattern = re.compile(r'[^\w\s\d.,!?;:()\'\"\-\+\*\/\\=áàâãéèêíóòôõúüçÁÀÂÃÉÈÊÍÓÒÔÕÚÜÇ\n]', re.UNICODE)
    sanitized = allowed_pattern.sub('', text)
    # Remove espaços duplos extras
    return re.sub(r' +', ' ', sanitized)


def _build_drawtext_filter(
    text: str,
    style: dict,
    face_position: str,
    video_width: int,
    video_height: int,
    font_path: str,
) -> str:
    # Sanitiza o texto de emojis e caracteres especiais antes de formatar
    text = _sanitize_text_for_ffmpeg(text)

    max_line_chars = 32
    wrapped_text = _wrap_text(text, max_chars_per_line=max_line_chars)
    lines = [line.strip() for line in wrapped_text.split("\n") if line.strip()]

    if not lines:
        return f"drawtext=fontfile={font_path}:text='':x=0:y=0"

    size_label = style.get("font_size_relative", "medium")
    base_ratio = SIZE_RATIOS.get(size_label, SIZE_RATIOS["medium"])
    font_size = _responsive_font_size(lines, video_width, video_height, base_ratio)

    color = _normalize_color(style.get("font_color", "white"))
    has_box = style.get("has_background_box", False)

    vertical = style.get("position_vertical", "bottom")
    horizontal = style.get("position_horizontal", "center")

    # Avoid placing text where the face is
    if vertical == "top" and face_position in ("top", "center"):
        vertical = "bottom"
    elif vertical == "bottom" and face_position == "bottom":
        vertical = "top"

    padding_pct = int(style.get("padding_from_edge", 5))
    padding = int(video_height * (padding_pct / 100))
    
    if vertical == "bottom":
        # Margem de segurança de ~16% para não ser coberta pela interface do Instagram Reels (nome de usuário, legenda, etc.)
        safe_padding = int(video_height * 0.16)
        padding = max(padding, safe_padding)
    elif vertical == "top":
        # Margem de segurança de ~14% no topo para não ser coberta pelo header do Reels (botões, barra de status, etc.)
        safe_top_padding = int(video_height * 0.14)
        padding = max(padding, safe_top_padding)
    else:
        padding = max(40, min(padding, 120))  # keep text within a reasonable margin

    line_spacing = int(font_size * 0.2)
    total_height = len(lines) * font_size + (len(lines) - 1) * line_spacing

    if vertical == "top":
        base_y = padding
    elif vertical == "bottom":
        base_y = video_height - padding - total_height
    else:
        base_y = (video_height - total_height) / 2

    # Determine x position expression
    if horizontal == "left":
        x_expr = str(padding)
    elif horizontal == "right":
        x_expr = f"w-text_w-{padding}"
    else:
        x_expr = "(w-text_w)/2"

    if has_box:
        extras = "box=1:boxcolor=black@0.65:boxborderw=10"
    else:
        # Sombreado grosso e profissional estilo Reels (Stroke / Borda espessa + Sombra 3D leve)
        border_w = max(4, int(font_size * 0.11))
        extras = f"bordercolor=black:borderw={border_w}:shadowcolor=black@0.4:shadowx=2:shadowy=2"

    line_filters = []
    for i, line in enumerate(lines):
        y_val = int(base_y + i * (font_size + line_spacing))
        safe_line = line.replace("\\", "\\\\").replace("'", "'\\''").replace(":", "\\:")
        
        line_filter = (
            f"drawtext=fontfile={font_path}:"
            f"text='{safe_line}':"
            f"fontcolor={color}:fontsize={font_size}:"
            f"{extras}:"
            f"x={x_expr}:"
            f"y={y_val}"
        )
        line_filters.append(line_filter)

    return ",".join(line_filters)


def _wrap_text(text: str, max_chars_per_line: int = 32) -> str:
    # Normalize both real newlines and escaped \n from OCR
    raw_lines = text.replace("\r\n", "\n").replace("\\n", "\n").split("\n")
    result_lines: list[str] = []
    for raw_line in raw_lines:
        words = raw_line.split()
        current = ""
        for word in words:
            if len(current) + len(word) + (1 if current else 0) > max_chars_per_line:
                if current:
                    result_lines.append(current)
                current = word
            else:
                current = f"{current} {word}" if current else word
        if current:
            result_lines.append(current)
    return "\n".join(result_lines)


def _responsive_font_size(
    lines: list[str],
    video_width: int,
    video_height: int,
    base_ratio: float,
) -> int:
    if not lines:
        return 48

    n_lines = len(lines)
    longest = max((len(line) for line in lines), default=1)

    base_size = int(video_height * base_ratio)

    # Fit inside a safe text area (max 38% of video height)
    max_block_height = video_height * 0.38
    available_height_per_line = max_block_height / n_lines
    fit_by_height = int(available_height_per_line / 1.3)

    # Fit inside width (assume average glyph width ~0.55 * font_size)
    target_width = video_width * 0.88
    fit_by_width = int(target_width / (longest * 0.55))

    font_size = min(base_size, fit_by_height, fit_by_width)
    return max(26, min(font_size, 88))


def _normalize_color(color: str) -> str:
    mapping = {
        "branco": "white",
        "preto": "black",
        "amarelo": "yellow",
        "vermelho": "red",
        "verde": "green",
        "azul": "blue",
        "ciano": "cyan",
        "magenta": "magenta",
        "laranja": "orange",
    }
    normalized = mapping.get(color.lower().strip(), color.lower().strip())
    allowed = {"white", "black", "yellow", "red", "green", "blue", "cyan", "magenta", "orange"}
    return normalized if normalized in allowed else "white"


def _horizontal_position(horizontal: str, padding: int) -> str:
    if horizontal == "left":
        return str(padding)
    if horizontal == "right":
        return f"w-text_w-{padding}"
    return "(w-text_w)/2"


def _vertical_position(vertical: str, padding: int) -> str:
    if vertical == "top":
        return str(padding)
    if vertical == "bottom":
        return f"h-text_h-{padding}"
    return "(h-text_h)/2"
