from __future__ import annotations

import shutil
from pathlib import Path

from src.editing.timeline import MontageTimeline
from src.utils.ffmpeg_utils import FFmpegError, ensure_ffmpeg, run_ffmpeg


def render_timeline(
    timeline: MontageTimeline,
    output_path: str | Path,
    tmp_dir: str | Path | None = None,
    keep_tmp: bool = False,
) -> Path:
    """Render a montage timeline with FFmpeg."""
    ensure_ffmpeg()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if not timeline.clips:
        raise ValueError("Timeline has no clips to render.")

    work_dir = Path(tmp_dir) if tmp_dir else output.parent / "tmp"
    work_dir.mkdir(parents=True, exist_ok=True)
    segment_paths: list[Path] = []

    try:
        for index, clip in enumerate(timeline.clips):
            segment_path = work_dir / f"segment_{index:03d}.mp4"
            duration = max(0.1, clip.source_end - clip.source_start)
            print(f"[render] cutting {clip.clip_path} at {clip.source_start:.3f}s for {duration:.3f}s")
            run_ffmpeg([
                "-y",
                "-ss", f"{clip.source_start:.3f}",
                "-i", clip.clip_path,
                "-t", f"{duration:.3f}",
                "-vf", _scale_filter(timeline.export_resolution, timeline.export_fps),
                "-an",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                str(segment_path),
            ])
            segment_paths.append(segment_path)

        concat_file = work_dir / "concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{path.as_posix()}'" for path in segment_paths),
            encoding="utf-8",
        )
        joined_video = work_dir / "joined_video.mp4"
        print("[render] concatenating segments")
        run_ffmpeg([
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(joined_video),
        ])

        print("[render] adding music")
        run_ffmpeg([
            "-y",
            "-i", str(joined_video),
            "-i", timeline.music_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output),
        ])
    except FFmpegError:
        print(f"[render] failed. Temporary files kept at: {work_dir}")
        raise
    finally:
        if not keep_tmp and output.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

    return output


def _scale_filter(resolution: str, fps: int) -> str:
    width, height = _parse_resolution(resolution)
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={int(fps)}"
    )


def _parse_resolution(resolution: str) -> tuple[int, int]:
    try:
        width_text, height_text = resolution.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except Exception as exc:
        raise ValueError(f"Resolution must look like 1920x1080, got: {resolution}") from exc
    if width <= 0 or height <= 0:
        raise ValueError(f"Resolution values must be positive, got: {resolution}")
    return width, height

