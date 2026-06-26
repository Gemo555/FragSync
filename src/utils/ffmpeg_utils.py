from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    """Raised when FFmpeg/FFprobe is missing or exits with an error."""


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegError(
            "FFmpeg was not found on PATH. Install it first, for example: "
            "winget install Gyan.FFmpeg"
        )
    if shutil.which("ffprobe") is None:
        raise FFmpegError("FFprobe was not found on PATH. It is usually bundled with FFmpeg.")


def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess[str]:
    if shutil.which("ffmpeg") is None:
        raise FFmpegError("FFmpeg was not found on PATH.")
    command = ["ffmpeg", *args]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise FFmpegError(
            "FFmpeg command failed:\n"
            f"{' '.join(command)}\n\n"
            f"STDERR:\n{completed.stderr.strip()}"
        )
    return completed


def probe_duration(media_path: str | Path) -> float | None:
    if shutil.which("ffprobe") is None:
        return None
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None
    try:
        return float(completed.stdout.strip())
    except ValueError:
        return None

