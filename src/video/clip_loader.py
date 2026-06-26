from __future__ import annotations

from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}


def scan_clips(clips_dir: str | Path, max_clips: int | None = None) -> list[Path]:
    """Return supported video files in deterministic order."""
    root = Path(clips_dir)
    if not root.exists():
        raise FileNotFoundError(f"Clips folder not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Clips path is not a folder: {root}")

    clips = sorted(
        path for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    if max_clips is not None:
        clips = clips[:max(0, int(max_clips))]
    return clips

