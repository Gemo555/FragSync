from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MontageClip:
    clip_path: str
    source_start: float
    source_end: float
    event_time: float
    target_beat: float
    speed: float = 1.0
    effects: list[str] = field(default_factory=list)
    event_score: float = 0.0
    event_type: str = "unknown"

    @property
    def duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)


@dataclass
class MontageTimeline:
    music_path: str
    clips: list[MontageClip]
    export_resolution: str = "1920x1080"
    export_fps: int = 60
    style: str = "clean_sync"

    def to_dict(self) -> dict[str, Any]:
        return {
            "music_path": self.music_path,
            "clips": [asdict(clip) for clip in self.clips],
            "export_resolution": self.export_resolution,
            "export_fps": self.export_fps,
            "style": self.style,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MontageTimeline":
        clips = [MontageClip(**clip_data) for clip_data in data.get("clips", [])]
        return cls(
            music_path=data["music_path"],
            clips=clips,
            export_resolution=data.get("export_resolution", "1920x1080"),
            export_fps=int(data.get("export_fps", 60)),
            style=data.get("style", "clean_sync"),
        )

    def save_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "MontageTimeline":
        source = Path(path)
        data = json.loads(source.read_text(encoding="utf-8"))
        return cls.from_dict(data)

