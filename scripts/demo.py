from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    music = root / "data" / "music" / "song.mp3"
    clips = root / "data" / "clips"
    timeline = root / "data" / "output" / "timeline.json"

    if not music.exists():
        print(f"Add a music file first: {music}")
        return 1
    if not any(path.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"} for path in clips.iterdir()):
        print(f"Add short kill clips first: {clips}")
        return 1

    command = [
        sys.executable,
        "-m",
        "src.main",
        "--music",
        str(music),
        "--clips",
        str(clips),
        "--output",
        str(root / "data" / "output" / "montage.mp4"),
        "--manual-beats",
        str(root / "examples" / "manual_beats.json"),
        "--dry-run",
        "--export-timeline",
        str(timeline),
    ]
    print("Running dry-run demo:")
    print(" ".join(command))
    return subprocess.call(command, cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())

